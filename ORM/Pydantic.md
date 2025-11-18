[TOC]

# Pydantic-V2 升级指南

Pydantic-V2相比V1有如下变化：
Pydantic V2 相较于 Pydantic V1 有多个重大改进和不兼容变更（breaking changes），主要目标是提升性能、类型安全性和 API 的一致性。

以下是 Pydantic V2 与 V1 的一些关键区别：

（1）**底层依赖变更：从 `typing` 到 `pydantic-core`**

- **V1**：基于 Python 标准库的 `typing` 和自定义验证逻辑。
- **V2**：引入了用 Rust 编写的高性能核心库 `pydantic-core`，大幅提升了数据解析和验证速度（官方称快 5–10 倍）。

（2）**模型字段定义方式的变化**

 **V1（旧方式）**：

```
from pydantic import BaseModel, Field

class User(BaseModel):
    name: str
    age: int = Field(..., gt=0)
```

**V2（推荐方式）**：

- `Field` 的默认值行为更严格；
- 不再支持某些模糊的默认值写法（如 `Field(None)` 表示可选，现在需显式使用 `Optional` 或 `None` 类型注解）；
- 强烈建议使用类型注解配合 `Field()` 来表达约束。

```
from typing import Optional
from pydantic import BaseModel, Field

class User(BaseModel):
    name: str
    age: int = Field(gt=0)  # 必填，且 > 0
    email: Optional[str] = None  # 显式可选
```

（3）**验证器（Validators）语法变更**

**V1：**

```
from pydantic import validator

class Model(BaseModel):
    name: str

    @validator('name')
    def check_name(cls, v):
        assert v != 'forbidden'
        return v
```

**V2：**

- `@validator` 被弃用（但仍可用，但会警告）；
- 推荐使用新的 `@field_validator`（针对字段）或 `@model_validator`（针对整个模型）；
- 支持更灵活的模式（如 `mode='before'`, `'after'`, `'wrap'`）。

```
from pydantic import BaseModel, field_validator

class Model(BaseModel):
    name: str

    @field_validator('name')
    @classmethod
    def check_name(cls, v: str) -> str:
        if v == 'forbidden':
            raise ValueError('Name is forbidden')
        return v
```

（4）**配置项（Config）迁移为 `model_config`**

**V1：**

```
class Model(BaseModel):
    class Config:
        str_strip_whitespace = True
```

**V2：**

- 使用 `model_config` 字典或 `ConfigDict`；
- 配置项名称也有所调整（如 `allow_mutation` → `frozen`）。

```
from pydantic import BaseModel, ConfigDict

class Model(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, frozen=True)
    name: str
```

（5）**对 `None` 和可选字段的处理更严格**

- V2 中，如果字段类型是 `str`，但你传入 `None`，会直接报错（除非你明确声明为 `Optional[str]` 或 `str | None`）。
- V1 对此较为宽松，有时会隐式转换。

（6）**序列化（Serialization）行为变化**

- V2 引入了更强大的 `.model_dump()`（替代 `.dict()`）和 `.model_dump_json()`（替代 `.json()`）；
- 序列化选项通过 `mode` 参数控制（如 `mode='json'` vs `mode='python'`）；
- 更好地支持自定义序列化器。

（7）**插件系统与错误信息改进**

- V2 提供结构化的错误信息（`ValidationError.errors()` 返回更规范的列表）；
- 错误类型更细粒度，便于程序化处理；
- 支持自定义错误消息模板。

（8）**移除或弃用的功能**

- 移除了 `BaseSettings`（现由独立包 `pydantic-settings` 提供）；
- 不再支持 `@root_validator(pre=True)` 的某些旧用法；
- `parse_obj()`, `parse_raw()` 等方法被标记为 deprecated，推荐使用 `model_validate()`。

相应的`BaseSettings`的配置变化如下：

```python
# V1 的方式
from pydantic import BaseSettings
class AppSettingsV1(BaseSettings):
    class Config:
        env_file_encoding = "utf-8"
        case_sensitive = False

# V2 的方式
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettingsV2(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding='utf-8',
        case_sensitive=False
    )
```

**总结对比表**

| 特性   | Pydantic V1          | Pydantic V2                             |
|------|----------------------|-----------------------------------------|
| 核心引擎 | Python               | Rust (`pydantic-core`)                  |
| 性能   | 较慢                   | 快 5–10 倍                                |
| 验证器  | `@validator`         | `@field_validator` / `@model_validator` |
| 配置   | `class Config`       | `model_config = ConfigDict(...)`        |
| 序列化  | `.dict()`, `.json()` | `.model_dump()`, `.model_dump_json()`   |
| 可选字段 | 隐式容忍 `None`          | 必须显式声明 `Optional`                       |
| 设置管理 | `BaseSettings` 内置    | 移至 `pydantic-settings`                  |
| 类型安全 | 一般                   | 更强，更符合 PEP 484/585                      |