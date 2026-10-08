/* Demo SAS program: run Python pipeline first.
   Set ROOT to the absolute portfolio directory. SAS license required.
   Inputs are SDTM-like demo CSVs, not conformant submission datasets. */
%let root=CHANGE_TO_PORTFOLIO_DIRECTORY;
filename dmfile "&root./results/dm.csv";
filename aefile "&root./results/ae.csv";

data dm;
  infile dmfile dsd firstobs=2 truncover;
  length USUBJID $20 ARM $10 SEX $1 RFSTDTC $10;
  input USUBJID :$20. ARM :$10. AGE SEX :$1. RFSTDTC :$10.;
run;
data ae;
  infile aefile dsd firstobs=2 truncover;
  length USUBJID $20 AETERM $40 AESTDTC AEENDTC $10 AESEV $10;
  input USUBJID :$20. AESEQ AETERM :$40. AESTDTC :$10. AEENDTC :$10. AESEV :$10.;
run;
proc sql;
  create table denominator as
    select ARM, count(distinct USUBJID) as DENOMINATOR from dm group by ARM;
  create table affected as
    select d.ARM, count(distinct a.USUBJID) as SUBJECTS_WITH_AE
    from dm d inner join ae a on d.USUBJID=a.USUBJID
    where input(a.AEENDTC,yymmdd10.) >= input(a.AESTDTC,yymmdd10.)
    group by d.ARM;
  create table ae_summary as
    select d.ARM, d.DENOMINATOR,
           coalesce(a.SUBJECTS_WITH_AE,0) as SUBJECTS_WITH_AE,
           round(100*calculated SUBJECTS_WITH_AE/d.DENOMINATOR,0.1) as PERCENT
    from denominator d left join affected a on d.ARM=a.ARM order by d.ARM;
quit;
proc export data=ae_summary outfile="&root./results/ae_summary_sas.csv" dbms=csv replace;
run;
