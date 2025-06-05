## 常用语法


### 在模板中引用不希望被解析的内容时，可以使用 Jinja2 的 raw 块语法

```jinja2
{% raw %}
#!/bin/bash

# 你的脚本内容 ...
{% endraw %}
```

