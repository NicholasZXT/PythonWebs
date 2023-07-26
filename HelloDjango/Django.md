[TOC]


# Tips

个人练习Django的一些感受：
+ Django提供了开箱即用的 Admin 模块和对应的管理界面，还提供了 User 类和对应的认证机制，方便快速开发
+ Django整个框架和它底层ORM的耦合程度比较高，大部分操作都依赖于底层的ORM，特别是 Admin 界面和用户认证，这部分封装的比较深
+ 相比于Flask，Django比较规范，不过也缺少了自由度，比如在Flask中，我可以自由操作数据库，用或者不用ORM都可以，特别是快速开发的时候，不需要每次表变动，都需要去更新ORM里定义的Models

---

# 基础

> 此练习项目来自于胡阳《Django企业开发实战》里的typeidea博客.

+ 初始化项目   
使用`django-admin startproject <proj_name> [directory]` 命令生成项目。   
  + 如果只指定`proj_name`，则会在当前目录下，创建一个 `proj_name` 的文件夹作为项目根目录，其中生成一个`proj_name`子文件夹存放具体的项目和一个`manage.py`文件用于管理项目；    
  + 如果同时指定了`directory`，则会使用指定的目录作为项目根目录，在里面创建`manage.py`和`proc_name`文件夹

---

# Django REST Framework (DRF)

## 安装

```shell
# pip
pip install djangorestframework
# conda
conda install -c conda-forge djangorestframework
```
