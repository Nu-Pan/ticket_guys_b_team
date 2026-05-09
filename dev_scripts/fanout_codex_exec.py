# std
import argparse
import datetime
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, TextIO


TGBT_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = TGBT_ROOT / "dev_scripts" / "logs" / "fanout-file-codex"


@dataclass(frozen=True)
class FanoutTarget:
    """fanout の 1 回分の Codex 呼び出し対象。"""

    prompt: str
    commit_label: str


def main() -> int:
    """ファイル単位の Codex fanout 処理を実行する。"""
    # 呼び出し元の cwd に依存せず、fanout の処理起点を tgbt root に揃える。
    os.chdir(TGBT_ROOT)

    # 引数として作業タイプだけを受け取る。
    parser = argparse.ArgumentParser(
        description="Run codex exec for each target file or directory.",
    )
    parser.add_argument(
        "subcommand",
        choices=[
            "update-oracle-docs-routing",
            "create-repo-local-skill",
            "apply-oracle-to-implements-light",
            "apply-oracle-to-implements-heavy",
        ],
    )
    args = parser.parse_args()

    # 集約ログは標準出力と同じ内容を後で確認できるように残す。
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / _build_log_file_name(args.subcommand)
    with log_path.open("w", encoding="utf-8") as log_file:
        runner = FanoutRunner(args.subcommand, log_path, log_file)
        return runner.run()


class FanoutRunner:
    """fanout の git 操作、Codex 実行、ログ出力をまとめて扱う。"""

    def __init__(
        self,
        subcommand: str,
        log_path: Path,
        log_file: TextIO,
    ) -> None:
        """実行対象サブコマンドと集約ログを保持する。"""
        # 実行中に必要な subcommand とログ出力先を runner に保持する。
        self.subcommand = subcommand
        self.log_path = log_path
        self.log_file = log_file

    def run(self) -> int:
        """サブコマンドに対応する fanout 処理全体を実行する。"""
        # fanout 開始前に実行条件と起点ブランチを確定する。
        self._write_line(f"tgbt root: {TGBT_ROOT}")
        self._write_line(f"subcommand: {self.subcommand}")

        try:
            self._ensure_clean_worktree()
            branch_name = self._create_fanout_branch()
            targets = self._build_targets()
        except FanoutError as error:
            self._write_line(f"ERROR: {error}")
            self._write_line(f"log file: {self.log_path}")
            return 1

        # 個別 Codex 呼び出しは常に clean な git 状態から開始する。
        failures = 0
        self._write_line(f"fanout branch: {branch_name}")
        self._write_line(f"target count: {len(targets)}")
        for index, target in enumerate(targets, start=1):
            self._write_line("")
            self._write_line(f"target {index}/{len(targets)}: {target.commit_label}")
            if self._run_one_target(target):
                self._commit_target_changes(target)
            else:
                failures += 1
                self._discard_target_changes()

        self._write_line("")
        self._write_line(f"completed targets: {len(targets) - failures}")
        self._write_line(f"failed targets: {failures}")
        self._write_line(f"log file: {self.log_path}")
        if failures > 0:
            return 1
        return 0

    def _build_targets(self) -> list[FanoutTarget]:
        """サブコマンド名を具体的な Codex 呼び出し対象へ展開する。"""
        # fanout 対象を、サブコマンドごとの最小処理単位へ分解する。
        if self.subcommand == "update-oracle-docs-routing":
            return [
                FanoutTarget(
                    prompt=(
                        f"`{_tgbt_notation_path(path)}` だけを対象にスキル "
                        "$update-oracle-docs-routing を実行してください。"
                    ),
                    commit_label=_tgbt_notation_path(path),
                )
                for path in _oracle_docs_dirs()
            ]

        if self.subcommand == "create-repo-local-skill":
            return [
                FanoutTarget(
                    prompt=(
                        f"`{_tgbt_notation_path(path)}` だけを対象にスキル "
                        "$create-repo-local-skill と $skill-creator を"
                        "併用して実行してください。"
                    ),
                    commit_label=_tgbt_notation_path(path),
                )
                for path in _repo_local_skill_dirs()
            ]

        if self.subcommand == "apply-oracle-to-implements-light":
            return [
                FanoutTarget(
                    prompt=(
                        f"`{_tgbt_notation_path(path)}` だけを対象にスキル "
                        "$apply-oracle-to-implements を実行してください。"
                    ),
                    commit_label=_tgbt_notation_path(path),
                )
                for path in _oracle_docs_markdown_files()
            ]

        if self.subcommand == "apply-oracle-to-implements-heavy":
            targets: list[FanoutTarget] = []
            for oracle_path in _oracle_docs_markdown_files():
                for source_path in _tracked_src_python_files():
                    targets.append(
                        FanoutTarget(
                            prompt=(
                                "スキル $apply-oracle-to-implements を使用し、 "
                                f"`{_tgbt_notation_path(source_path)}` が "
                                f"`{_tgbt_notation_path(oracle_path)}` の内容と"
                                "整合するかチェックし、必要があれば修正してください。"
                            ),
                            commit_label=(
                                f"{_tgbt_notation_path(source_path)} vs "
                                f"{_tgbt_notation_path(oracle_path)}"
                            ),
                        )
                    )
            return targets

        raise FanoutError(f"unknown subcommand: {self.subcommand}")

    def _run_one_target(self, target: FanoutTarget) -> bool:
        """1 対象分の Codex CLI を実行し、標準出力へ tee する。"""
        # fanout は tgbt 本体仕様から独立した開発補助スクリプトとして Codex を呼ぶ。
        env = os.environ.copy()

        # tgbt profile には依存せず、fanout に必要な実行条件を CLI 引数で固定する。
        command = [
            "codex",
            "exec",
            "--model",
            "gpt-5.5",
            "-c",
            'model_reasoning_effort="medium"',
            "-c",
            'plan_mode_reasoning_effort="medium"',
            "--ignore-user-config",
            "--ephemeral",
            "--cd",
            str(TGBT_ROOT),
        ]
        if self.subcommand == "create-repo-local-skill":
            command.append("--dangerously-bypass-approvals-and-sandbox")
        else:
            command.extend(
                [
                    "-c",
                    'approval_policy="never"',
                    "-c",
                    "sandbox_workspace_write.network_access=true",
                    "--sandbox",
                    "workspace-write",
                ],
            )
        command.append(target.prompt)

        self._write_line(f"command: {_format_command(command)}")
        process = subprocess.Popen(
            command,
            cwd=TGBT_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        if process.stdout is None:
            raise FanoutError("failed to capture codex stdout")

        # Codex の出力を人間の端末と集約ログの両方へ逐次流す。
        for line in process.stdout:
            self._write(line)
        returncode = process.wait()
        self._write_line(f"returncode: {returncode}")
        return returncode == 0

    def _commit_target_changes(self, target: FanoutTarget) -> None:
        """成功した対象で発生した変更をコミットする。"""
        # 変更が無ければコミットせず、clean な状態のまま次へ進める。
        if not _has_uncommitted_changes():
            self._write_line("no changes to commit")
            return

        _run_git(["add", "-A"])
        message = f"fanout {self.subcommand}: {target.commit_label}"
        completed = _run_git(["commit", "-m", message], check=False)
        self._write(completed.stdout)
        self._write(completed.stderr)
        if completed.returncode != 0:
            raise FanoutError("git commit failed")

    def _discard_target_changes(self) -> None:
        """失敗した対象で発生した未コミット変更を破棄する。"""
        # fanout 仕様上、失敗時は次の対象へ clean な状態で進む。
        self._write_line("discarding uncommitted changes")
        _run_git(["reset", "--hard", "HEAD"])
        _run_git(["clean", "-fd"])

    def _ensure_clean_worktree(self) -> None:
        """fanout 開始時点の git 状態が clean であることを確認する。"""
        # 未コミット変更がある状態では fanout の対象間分離を保証できない。
        status = _git_stdout(["status", "--porcelain"])
        if status:
            raise FanoutError(
                "git worktree is not clean. "
                "Commit or discard changes before running fanout.",
            )

    def _create_fanout_branch(self) -> str:
        """ローカル default branch から fanout 専用ブランチを作成する。"""
        # remote HEAD から対応するローカル default branch 名を得る。
        remote_default = _git_stdout(
            ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
        )
        if "/" not in remote_default:
            raise FanoutError("failed to resolve origin default branch")
        default_branch = remote_default.split("/", maxsplit=1)[1]

        # ローカル default branch の最新コミットを起点にする。
        branches = _git_stdout(["branch", "--format=%(refname:short)"]).splitlines()
        if default_branch not in branches:
            raise FanoutError(f"local default branch not found: {default_branch}")
        _run_git(["switch", default_branch])

        branch_name = f"fanout-file-codex/{self.subcommand}-{_timestamp_slug()}"
        _run_git(["switch", "-c", branch_name])
        return branch_name

    def _write_line(self, message: str) -> None:
        """標準出力とログへ 1 行を書き出す。"""
        # 行単位の呼び出し元向けに改行を付けて共通 writer へ渡す。
        self._write(f"{message}\n")

    def _write(self, message: str) -> None:
        """標準出力とログへ同じ内容を書き出す。"""
        # terminal と永続ログの両方へ同じ message を即時反映する。
        print(message, end="", flush=True)
        self.log_file.write(message)
        self.log_file.flush()


class FanoutError(Exception):
    """fanout 実行を継続できないエラー。"""


def _oracle_docs_dirs() -> list[Path]:
    """oracle/docs 配下の全ディレクトリを絶対パスで返す。"""
    # docs root 自体も ROUTING.md 更新対象なので、子ディレクトリと合わせて返す。
    docs_root = TGBT_ROOT / "oracle" / "docs"
    return sorted(
        [docs_root, *[path for path in docs_root.rglob("*") if path.is_dir()]],
    )


def _repo_local_skill_dirs() -> list[Path]:
    """repo-local skill 直下のディレクトリを絶対パスで返す。"""
    # repo-local skill root がまだ無い場合は fanout 対象なしとして扱う。
    skills_root = TGBT_ROOT / ".agents" / "skills"
    if not skills_root.exists():
        return []
    return sorted([path for path in skills_root.iterdir() if path.is_dir()])


def _oracle_docs_markdown_files() -> list[Path]:
    """ROUTING.md を除いた oracle/docs 配下の Markdown を返す。"""
    # 各階層の目次である ROUTING.md は oracle 適用対象から除外する。
    docs_root = TGBT_ROOT / "oracle" / "docs"
    return sorted(
        [
            path
            for path in docs_root.rglob("*.md")
            if path.name != "ROUTING.md"
        ],
    )


def _tracked_src_python_files() -> list[Path]:
    """git が追跡する src 配下の Python ファイルを返す。"""
    # git の追跡対象だけを使い、生成物や未追跡ファイルを fanout 対象から外す。
    output = _git_stdout(["ls-files", "-z", "--", "src"])
    relative_paths = [item for item in output.split("\0") if item.endswith(".py")]
    return [TGBT_ROOT / path for path in sorted(relative_paths)]


def _has_uncommitted_changes() -> bool:
    """git 上の未コミット変更が存在するかを返す。"""
    # porcelain 出力の有無だけで fanout 中の commit 要否を判定する。
    return bool(_git_stdout(["status", "--porcelain"]))


def _run_git(
    args: Sequence[str],
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """tgbt root で git コマンドを実行する。"""
    # subprocess 例外ではなく戻り値を見て、fanout 用のエラーへ変換する。
    completed = subprocess.run(
        ["git", *args],
        cwd=TGBT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and completed.returncode != 0:
        raise FanoutError(
            f"git {' '.join(args)} failed: "
            f"{completed.stderr.strip() or completed.stdout.strip()}",
        )
    return completed


def _git_stdout(args: Sequence[str]) -> str:
    """git コマンドの標準出力を末尾改行なしで返す。"""
    # 呼び出し元が git 出力を値として扱いやすいよう末尾空白を落とす。
    return _run_git(args).stdout.strip()


def _build_log_file_name(subcommand: str) -> str:
    """サブコマンド名を含むログファイル名を作る。"""
    # 複数回実行しても衝突しにくいよう timestamp を先頭に置く。
    return f"{_timestamp_slug()}-{subcommand}.log"


def _timestamp_slug() -> str:
    """ファイル名とブランチ名で使える UTC タイムスタンプを返す。"""
    # ローカル timezone の影響を避けるため UTC 固定で slug を作る。
    now = datetime.datetime.now(datetime.UTC)
    return now.strftime("%Y%m%dT%H%M%S%fZ")


def _tgbt_notation_path(path: Path) -> str:
    """`<tgbt-root>/...` 表記へ変換する。"""
    # oracle のパス表記ルールに従い、ticket_guys_b_team 配下の path として明示する。
    relative_path = os.fspath(path.relative_to(TGBT_ROOT))
    if relative_path == ".":
        return "<tgbt-root>"
    return f"<tgbt-root>/{relative_path}"


def _format_command(command: Sequence[str]) -> str:
    """ログ用にコマンド引数を読みやすく連結する。"""
    # fanout ログでは shell 実行用ではなく、人間が読む表示として連結する。
    return " ".join(command)


if __name__ == "__main__":
    sys.exit(main())
