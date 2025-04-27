## post_gen_project.py 说明


### 控制台脚本日志输出
   
```python
SUCCESS = " \x1b[1;32m [SUCCESS]: "  # 绿色加粗的 "[SUCCESS]: "
TERMINATOR = " \x1b[0m"              # 重置终端颜色
INFO = " \x1b[1;33m [INFO]: "        # 黄色加粗的 "[INFO]: "
```

ANSI 转义码说明​​  
* \x1b 是 ASCII 的 ​​ESC（Escape）字符​​，表示 ANSI 转义序列的开始。
* [ 是 ANSI 控制序列的起始符。

1;32m 是控制代码：  
  * 1 表示 ​​加粗（bold）​​。
  * 32 表示 ​​绿色（green）​​。
  * m 表示颜色/样式设置的结束。
  * 0m 表示 ​​重置所有样式​​（恢复终端默认颜色）。


### 递归删除指定的文件或目录​​（包括其所有子文件和子目录）

```python

def remove_files_and_folders(*paths: str, verbose: bool = False) -> None:
    for path in paths:
        p = Path(path).expanduser().resolve()  # 处理 ~ 和相对路径
        try:
            if p.is_dir():
                shutil.rmtree(p)
                if verbose:
                    print(f"Deleted directory: {p}")
            else:
                p.unlink()
                if verbose:
                    print(f"Deleted file: {p}")
        except Exception as e:
            print(f"Error deleting {p}: {e}")
```

> 注意事项​​：  
> * ​不可逆操作​​：删除的文件和目录无法恢复，请谨慎使用！  
> * ​权限问题​​：如果文件/目录被占用或无权限，可能会抛出 PermissionError。  
> * ​路径不存在​​：如果路径不存在，会抛出 FileNotFoundError（可先用 p.exists() 检查）。  
> * ​跨平台兼容​​：pathlib.Path 会自动处理不同操作系统的路径格式（如 \ 和 /）。 


### Path(path).expanduser().resolve() 与 Path(path) 区别


|           操作           | 处理 `~` 家目录 | 处理 `.`/`..` | 解析符号链接 | 返回绝对路径 |
| :----------------------: | :-------------: | :-----------: | :----------: | :----------: |
|       `Path(path)`       |        ❌        |       ❌       |      ❌       |      ❌       |
|      `expanduser()`      |        ✔️        |       ❌       |      ❌       |      ❌       |
|       `resolve()`        |        ❌        |       ✔️       |      ✔️       |      ✔️       |
| `expanduser().resolve()` |        ✔️        |       ✔️       |      ✔️       |      ✔️       |


* Path(path)：  
**作用**：简单地将字符串转换为 Path 对象，但不会处理用户目录和符号链接。  
**适用场景**：当你已经知道路径是绝对路径，并且不需要对路径进行任何展开或解析时，直接使用 Path(path) 是非常方便的。

* Path(path).expanduser().resolve()：  
**作用**：不仅将路径转换为 Path 对象，还会处理 ~ 用户目录、符号链接、相对路径等。  
**适用场景**：当你需要确保路径是绝对路径且已展开用户目录时，使用这个会更加健壮，特别是在处理用户目录路径或需要确保路径解析后的情况下。