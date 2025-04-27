from pathlib import Path
import shutil
import subprocess

SUCCESS = " \x1b[1;32m [SUCCESS]: " 
TERMINATOR = " \x1b[0m"
INFO = " \x1b[1;33m [INFO]: "


def remove_files_and_folders(*paths: str, verbose: bool = False) -> None:
    for path in paths:
        p = Path(path)  # 处理 ~ 和相对路径
        try:
            if p.is_dir():
                shutil.rmtree(p)
                if verbose:
                    print(f"删除目录: {p}")
            else:
                p.unlink()
                if verbose:
                    print(f"删除文件: {p}")
        except Exception as e:
            print(f"删除失败 {p}: {e}")


def remove_example_suffix():
    # 找到 .env.example 并重命名为 .env
    env_example = Path(".env.example")
    if env_example.exists():
        env_example.rename(".env")


def main():
    if "{{ cookiecutter.render_html is defined and cookiecutter.render_html }}" == "n":
        remove_files_and_folders("app/static", "app/frontend", "app/templates")

    # 重命名 .env.example -> .env
    remove_example_suffix()

    print(SUCCESS + "初始化成功, 继续努力！!" + TERMINATOR)
    print(
        INFO
        + "如果你喜欢这个项目，可以考虑Star在 https://github.com/tuonioooo/cookiecutter-base-fastapi"
        + TERMINATOR
    )


if __name__ == "__main__":
    main()
