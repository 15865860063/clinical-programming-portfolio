# Clinical Programming & Data Management Portfolio

![Validation](https://github.com/15865860063/clinical-programming-portfolio/actions/workflows/verify.yml/badge.svg)

用完全模拟的数据展示临床编程与数据管理核查。Python标准库即可运行，无第三方依赖。
这是个人作品，不是真实临床试验或注册申报交付。

## 快速运行

使用Python 3.12，在仓库目录执行：

```text
python -m unittest -v
python pipeline.py
```

输出至results/：DM/AE模拟数据、数据质疑清单、分组AE人数表、运行摘要。
预设120名受试者、3条异常；实际AE记录数及结果以运行输出为准。

## 技术内容

- 固定随机种子的模拟数据，可复现。
- 年龄范围、跨表关联、日期顺序核查。
- 基于唯一受试者的AE汇总，明确分母与异常处理口径。
- 六项自动测试覆盖异常定位、边界和统计计数逻辑。
- 同口径SAS汇总代码及Edit Check/UAT规范。
- GitHub Actions自动验证并保存结果artifact。

## 查看结果

进入[Actions](https://github.com/15865860063/clinical-programming-portfolio/actions)，
打开最新成功的运行，在Artifacts中下载synthetic-clinical-results。

## 验证状态

已确认[首次运行](https://github.com/15865860063/clinical-programming-portfolio/actions/runs/37749842185)成功：六项测试通过，生成120名受试者、184条AE记录与3条质疑。
详见[验证报告](docs/validation.md)及[简历项目草稿](docs/resume-projects-zh.md)。
SAS程序尚未在SAS环境运行；不得声称双程序验证通过。
本项目没有正式SDTM/ADaM合规验证、医学编码或真实EDC交付。

## 文件

- pipeline.py：模拟数据、核查、汇总。
- test_pipeline.py：六项验证测试。
- sas/ae_summary.sas：SAS汇总代码。
- docs/specification.md：数据约定、规则与范围。
- docs/deliverables.md：交付说明与面试讨论。

简历中应标注“个人模拟临床数据项目”，并在实际运行、理解代码后描述成果。
