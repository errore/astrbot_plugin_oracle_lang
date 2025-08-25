# AstrBot Oracle Lang Plugin (算卦插件)

这是一个基于易经原理的智能算卦插件，支持多种起卦方式，提供专业的卦象解读。本插件是从 [OracleLang](https://github.com/ydzat/OracleLang) 项目移植到 AstrBot 平台的版本。

## 原作者声明

- 原始项目: [OracleLang](https://github.com/ydzat/OracleLang)
- 原作者: [@ydzat](https://github.com/ydzat)
- 许可证: 与原项目保持一致

## 功能特点

- 支持多种起卦方式（文本、数字、时间）
- 专业的卦象解读
- 可选的 AI 增强解释
- 历史记录查询
- 使用次数限制
- 管理员功能

## 使用方法

### 基本指令

```
算卦 [问题]  - 使用文本起卦方式进行算卦
例如：算卦 我今天的工作运势如何？
      算卦 近期是否适合投资股票？
      算卦  (不提供问题将随缘生成一卦)
```

### 高级指令

```
算卦 数字 [数字] [问题]  - 使用指定数字起卦
例如：算卦 数字 1234 我的事业前景如何

算卦 时间 [时间] [问题]  - 使用当前时间起卦
例如：算卦 时间 明天 财运

算卦 历史  - 查看您的最近算卦记录
算卦 我的ID  - 查询您的用户ID
```

### 管理员指令

```
算卦 设置 次数 [数字]  - 设置每日算卦次数限制
算卦 重置 [用户ID]  - 重置特定用户的算卦次数
算卦 统计  - 查看使用统计信息
```

## 配置说明

插件使用 `_conf_schema.json` 进行配置，主要配置项包括：

1. admin_users: 管理员用户ID列表
2. limit: 使用限制相关配置
   - daily_max: 每日算卦次数限制
   - reset_time: 每日重置时间
3. llm: 大语言模型相关配置
   - enabled: 是否启用AI解释
4. display: 显示相关配置
   - style: 卦象显示风格 (unicode/text)

## 鸣谢

- 感谢 [@ydzat](https://github.com/ydzat) 开发的原始 OracleLang 插件
- 感谢 [AstrBot](https://github.com/AstrBotDevs/AstrBot) 团队提供的平台支持
