# 交付与面试讲解

|文件|用途|
|---|---|
|dm.csv / ae.csv|模拟输入，120名受试者|
|queries.csv|3条故意植入异常的核查清单|
|ae_summary.csv|以每组60人为分母的AE人数汇总|
|run_summary.json|规模、种子、异常数量和模拟标记|
|sas/ae_summary.sas|同口径SAS代码，未运行验证|
|Actions artifact|自动运行输出和CSV文件|

面试可讨论：为什么按人数而非事件条数统计；如何保留并追溯异常；
年龄资格异常为何不自动移出安全性总体；真实研究的排除规则如何由SAP约定；
SDTM-like与正式CDISC合规数据的区别；Python测试为什么不能代替独立SAS验证。

后续扩展：正式SDTM/ADaM映射、基线及变化值、TLF、外部数据对账、Query状态流转。
以上扩展目前尚未完成。
