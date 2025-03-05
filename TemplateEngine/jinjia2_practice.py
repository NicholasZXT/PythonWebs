"""
演示jinja2基本使用
"""
from jinja2 import Environment,  FileSystemLoader, PackageLoader, select_autoescape, Template

# ------ Step 1: 入口类 Environment ------
# 只有两个参数需要关注：
#  1. loader，从哪里加载template，常用的有 PackageLoader, FileSystemLoader
#  FileSystemLoader 指定从文件夹加载template，相对路径或绝对路径均可
loader = FileSystemLoader("templates")
# 也可以按顺序指定多个
# loader = FileSystemLoader(["/override/templates", "/default/templates"])
#  2. autoescape, 控制着模板输出的自动转义行为，主要用于增强 Web 应用程序的安全性，特别是防止跨站脚本攻击（XSS），一般默认即可
#  其他参数参见文档说明，都很好懂
env = Environment(
    loader=loader,
    autoescape=select_autoescape(),
    keep_trailing_newline=True
)

# ------ Step 2: 从 Environment 获取 template ------
template: Template = env.get_template("mytemplate.html")

# ------ Step 3: 渲染 template ------
# 参数为替换的变量
navigation = [{'href': '/', 'caption': 'Home'}, {'href': '/about', 'caption': 'about'}]
res: str = template.render(title="Jinja2 Demo", navigation=navigation)

print(res)
print("**************************************")


# --------- 下面有两个快捷使用方式，不过官方不怎么推荐 ---------
# --------- 快捷使用方式 1 ---------
source = """
<head>
    <meta charset="UTF-8">
    <title>{{ title }}</title>
</head>
"""
temp2 = env.from_string(source=source)
temp2_str = temp2.render(title="Jinja2 Demo 2")
print(temp2_str)
print("**************************************")

# --------- 快捷使用方式 2 ---------
temp3 = Template(source=source)
temp3_str = temp3.render(title="Jinja2 Demo 3")
print(temp3_str)
