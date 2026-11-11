# Schema mapping

Generated from `config/schema_mapping.yml` by `aco_scorecard/docs.py`. Do not edit by hand.

CMS publishes one Performance Year Financial and Quality Results file per performance period. Between PY 2013 and
PY 2024 the files renamed columns (for example `ACO_NAME` to `ACO_Name`, `N_AB_Year` to `N_AB_Year_PY`, `Sav_rate` to
`Sav_Rate` and back), changed units (rates published as fractions in some years and percents in others, with and
without a `%` sign), switched identifiers (encrypted `ACO_Num` through PY 2017, unencrypted `ACO_ID` from PY 2018),
recoded tracks (0/1 flags through PY 2021, a single code from PY 2022) and replaced the quality measure set in PY 2021.
Every one of those decisions is recorded below, period by period. The loader refuses a file if any column named here is
missing, and the dbt tests check that every rate lands on the expected scale in every period.

Mapping version: 2026-11-03. Periods: 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2019A, 2020, 2021, 2022, 2023, 2024.

## Financial, attribution and population fields

| canonical column | type | unit | source by period |
|---|---|---|---|
| `aco_source_id` | varchar |  | 2013 to 2017: `ACO_Num`; 2018 to 2024: `ACO_ID` |
| `aco_name` | varchar |  | 2013 to 2014: `ACO_NAME`; 2015 to 2024: `ACO_Name` |
| `aco_states_text` | varchar |  | 2013: not published; 2014 to 2021: `ACO_State`; 2022 to 2024: not published |
| `agreement_type` | varchar |  | 2013 to 2015: not published; 2016 to 2024: `Agree_Type` |
| `agreement_period_num` | number |  | 2013 to 2015: not published; 2016 to 2024: `Agreement_Period_Num` |
| `initial_start_date` | date |  | 2013 to 2015: `Start_Date`; 2016 to 2021: `Initial_Start_Date`; 2022 to 2024: not published |
| `current_start_date` | date |  | 2013 to 2015: `Start_Date`; 2016 to 2024: `Current_Start_Date` |
| `risk_model_reported` | varchar |  | 2013 to 2018: not published; 2019 to 2024: `Risk_Model` |
| `assignment_type` | varchar |  | 2013 to 2020: not published; 2021 to 2024: `Assign_Type` |
| `snf_waiver_flag` | flag |  | 2013 to 2017: not published; 2018 to 2024: `SNF_Waiver` |
| `six_month_flag` | flag |  | 2013 to 2018: not published; 2019 to 2019A: `Participation_Six_Months`; 2020 to 2024: not published |
| `revenue_category` | varchar |  | 2013 to 2017: not published; 2018 to 2024: `Rev_Exp_Cat` |
| `n_assigned_beneficiaries` | number |  | 2013 to 2024: `N_AB` |
| `person_years` | number |  | 2013 to 2014: `N_AB_Year`; 2015 to 2024: `N_AB_Year_PY` |
| `total_benchmark_expenditures` | number | dollars | 2013 to 2024: `ABtotBnchmk` |
| `total_expenditures` | number | dollars | 2013 to 2024: `ABtotExp` |
| `benchmark_minus_expenditures` | number | dollars | 2013 to 2024: `BnchmkMinExp` |
| `savings_rate_reported` | number | fraction | 2013: not published; 2014 to 2015: `Sav_rate` (percent, divided by 100); 2016 to 2019: `Sav_rate`; 2019A: `Sav_rate` (percent, divided by 100); 2020: `Sav_rate`; 2021: `Sav_Rate` (percent, divided by 100); 2022 to 2024: `Sav_rate` (percent, divided by 100) |
| `min_savings_rate` | number | fraction | 2013: `MinSavPerc`; 2014 to 2015: `MinSavPerc` (percent, divided by 100); 2016 to 2019: `MinSavPerc`; 2019A: `MinSavPerc` (percent, divided by 100); 2020: `MinSavPerc`; 2021 to 2024: `MinSavPerc` (percent, divided by 100) |
| `generated_savings_losses` | number | dollars | 2013: not published; 2014 to 2024: `GenSaveLoss` |
| `earned_savings_losses` | number | dollars | 2013: `coalesce(EarnShrSavings, 0) + coalesce(OweLosses, 0)`; 2014 to 2024: `EarnSaveLoss` |
| `max_sharing_rate_reported` | number | fraction | 2013 to 2014: `QualPerfShare`; 2015: `QualPerfShare` (percent, divided by 100); 2016 to 2019: `QualPerfShare`; 2019A: `QualPerfShare` (percent, divided by 100); 2020: `QualPerfShare`; 2021: `MaxShareRate` (percent, divided by 100); 2022 to 2024: not published |
| `final_sharing_rate` | number | fraction | 2013 to 2014: `FinalShareRate`; 2015: `FinalShareRate` (percent, divided by 100); 2016 to 2019: `FinalShareRate`; 2019A: `FinalShareRate` (percent, divided by 100); 2020: `FinalShareRate`; 2021 to 2024: `FinalShareRate` (percent, divided by 100) |
| `final_loss_rate` | number | fraction | 2013 to 2022: not published; 2023 to 2024: `FinalLossRate` (percent, divided by 100) |
| `updated_benchmark_per_capita` | number | dollars | 2013: not published; 2014 to 2024: `UpdatedBnchmk` |
| `historical_benchmark_per_capita` | number | dollars | 2013: not published; 2014 to 2024: `HistBnchmk` |
| `per_capita_expenditure_reported` | number | dollars | 2013: not published; 2014 to 2024: `Per_Capita_Exp_TOTAL_PY` |
| `quality_score` | number | points_0_100 | 2013 to 2014: `QualScore` (fraction, times 100); 2015: `QualScore`; 2016 to 2018: `QualScore` (fraction, times 100); 2019 to 2024: `QualScore` |
| `quality_score_raw` | varchar |  | 2013 to 2024: `QualScore` |
| `met_quality_standard_flag` | flag |  | 2013 to 2015: not published; 2016 to 2024: `Met_QPS` |
| `reduced_shared_savings_flag` | flag |  | 2013 to 2023: not published; 2024: `ReducedSS` |
| `pct_dual_eligible` | number | fraction | 2013 to 2020: not published; 2021 to 2024: `Perc_Dual` (percent, divided by 100) |
| `n_beneficiaries_age_0_64` | number |  | 2013 to 2024: `N_Ben_Age_0_64` |
| `n_beneficiaries_age_65_74` | number |  | 2013 to 2024: `N_Ben_Age_65_74` |
| `n_beneficiaries_age_75_84` | number |  | 2013 to 2024: `N_Ben_Age_75_84` |
| `n_beneficiaries_age_85_plus` | number |  | 2013 to 2024: `N_Ben_Age_85plus` |
| `inpatient_discharges_per_1000` | number |  | 2013 to 2024: `ADM` |
| `ed_visits_per_1000` | number |  | 2013 to 2024: `P_EDV_Vis` |
| `primary_care_services_per_1000` | number |  | 2013 to 2024: `P_EM_Total` |
| `pcp_services_per_1000` | number |  | 2013 to 2024: `P_EM_PCP_Vis` |
| `n_primary_care_physicians` | number |  | 2013 to 2024: `N_PCP` |
| `n_specialists` | number |  | 2013 to 2024: `N_Spec` |
| `person_years_esrd` | number |  | 2013 to 2014: `N_AB_Year_ESRD`; 2015 to 2024: `N_AB_Year_ESRD_PY` |
| `person_years_disabled` | number |  | 2013 to 2014: `N_AB_Year_DIS`; 2015 to 2024: `N_AB_Year_DIS_PY` |
| `person_years_aged_dual` | number |  | 2013 to 2014: `N_AB_Year_AGED_Dual`; 2015 to 2024: `N_AB_Year_AGED_Dual_PY` |
| `person_years_aged_nondual` | number |  | 2013 to 2014: `N_AB_Year_AGED_NonDual`; 2015 to 2024: `N_AB_Year_AGED_NonDual_PY` |
| `per_capita_exp_esrd` | number | dollars | 2013: `Per_Capita_Exp_ALL_ESRD`; 2014 to 2024: `Per_Capita_Exp_ALL_ESRD_PY` |
| `per_capita_exp_disabled` | number | dollars | 2013: `Per_Capita_Exp_ALL_DIS`; 2014 to 2024: `Per_Capita_Exp_ALL_DIS_PY` |
| `per_capita_exp_aged_dual` | number | dollars | 2013: `Per_Capita_Exp_ALL_AGDU`; 2014 to 2024: `Per_Capita_Exp_ALL_AGDU_PY` |
| `per_capita_exp_aged_nondual` | number | dollars | 2013: `Per_Capita_Exp_ALL_AGND`; 2014 to 2024: `Per_Capita_Exp_ALL_AGND_PY` |
| `risk_score_esrd` | number |  | 2013 to 2024: `CMS_HCC_RiskScore_ESRD_PY` |
| `risk_score_disabled` | number |  | 2013 to 2024: `CMS_HCC_RiskScore_DIS_PY` |
| `risk_score_aged_dual` | number |  | 2013 to 2024: `CMS_HCC_RiskScore_AGDU_PY` |
| `risk_score_aged_nondual` | number |  | 2013 to 2024: `CMS_HCC_RiskScore_AGND_PY` |
| `risk_score_esrd_by3` | number |  | 2013 to 2024: `CMS_HCC_RiskScore_ESRD_BY3` |
| `risk_score_disabled_by3` | number |  | 2013 to 2024: `CMS_HCC_RiskScore_DIS_BY3` |
| `risk_score_aged_dual_by3` | number |  | 2013 to 2024: `CMS_HCC_RiskScore_AGDU_BY3` |
| `risk_score_aged_nondual_by3` | number |  | 2013 to 2024: `CMS_HCC_RiskScore_AGND_BY3` |
| `person_years_esrd_by3` | number |  | 2013: not published; 2014 to 2024: `N_AB_Year_ESRD_BY3` |
| `person_years_disabled_by3` | number |  | 2013: not published; 2014 to 2024: `N_AB_Year_DIS_BY3` |
| `person_years_aged_dual_by3` | number |  | 2013: not published; 2014 to 2024: `N_AB_Year_AGED_Dual_BY3` |
| `person_years_aged_nondual_by3` | number |  | 2013: not published; 2014 to 2024: `N_AB_Year_AGED_NonDual_BY3` |
| `per_capita_exp_esrd_by3` | number | dollars | 2013: not published; 2014 to 2024: `Per_Capita_Exp_ALL_ESRD_BY3` |
| `per_capita_exp_disabled_by3` | number | dollars | 2013: not published; 2014 to 2024: `Per_Capita_Exp_ALL_DIS_BY3` |
| `per_capita_exp_aged_dual_by3` | number | dollars | 2013: not published; 2014 to 2024: `Per_Capita_Exp_ALL_AGDU_BY3` |
| `per_capita_exp_aged_nondual_by3` | number | dollars | 2013: not published; 2014 to 2024: `Per_Capita_Exp_ALL_AGND_BY3` |

## Track decoding

| periods | rule |
|---|---|
| 2013 | 0/1 flags: `Track2` = TRACK_2; none set = TRACK_1 |
| 2014 to 2015 | 0/1 flags: `Track1` = TRACK_1, `Track2` = TRACK_2 |
| 2016 to 2017 | 0/1 flags: `Current_Track_1` = TRACK_1, `Current_Track_2` = TRACK_2, `Current_Track_3` = TRACK_3 |
| 2018 | 0/1 flags: `Current_Track_1` = TRACK_1, `Current_Track_2` = TRACK_2, `Current_Track_3` = TRACK_3, `Current_Track_1_Plus` = TRACK_1_PLUS |
| 2019 to 2021 | 0/1 flags: `Current_Track_1` = TRACK_1, `Current_Track_2` = TRACK_2, `Current_Track_3` = TRACK_3, `Current_Track_1_Plus` = TRACK_1_PLUS, `Current_BASIC_A` = BASIC_A, `Current_BASIC_B` = BASIC_B, `Current_BASIC_C` = BASIC_C, `Current_BASIC_D` = BASIC_D, `Current_BASIC_E` = BASIC_E, `Current_ENHANCED` = ENHANCED |
| 2022 to 2024 | code column `Current_Track`: A = BASIC_A, B = BASIC_B, C = BASIC_C, D = BASIC_D, E = BASIC_E, EN = ENHANCED |

## Quality measure columns

Legacy ACO measure columns (PY 2016 to 2020) map to their APM Performance Pathway names using the crosswalk printed in
the CMS PY 2021 data dictionary notes. Measure level results are not published for PY 2013 to 2015.

| measure key | collection | source by period |
|---|---|---|
| `CAHPS_1` | CAHPS survey | 2016 to 2020: `ACO1`; 2021 to 2024: `CAHPS_1` |
| `CAHPS_2` | CAHPS survey | 2016 to 2020: `ACO2`; 2021 to 2024: `CAHPS_2` |
| `CAHPS_3` | CAHPS survey | 2016 to 2020: `ACO3`; 2021 to 2024: `CAHPS_3` |
| `CAHPS_4` | CAHPS survey | 2016 to 2020: `ACO4`; 2021 to 2024: `CAHPS_4` |
| `CAHPS_5` | CAHPS survey | 2016 to 2020: `ACO5`; 2021 to 2024: `CAHPS_5` |
| `CAHPS_6` | CAHPS survey | 2016 to 2020: `ACO6`; 2021 to 2024: `CAHPS_6` |
| `CAHPS_7` | CAHPS survey | 2016 to 2020: `ACO7`; 2021 to 2024: `CAHPS_7` |
| `CAHPS_11` | CAHPS survey | 2016 to 2020: `ACO34`; 2021 to 2024: `CAHPS_11` |
| `CAHPS_9` | CAHPS survey | 2019 to 2020: `ACO45`; 2021 to 2024: `CAHPS_9` |
| `CAHPS_8` | CAHPS survey | 2019 to 2020: `ACO46`; 2021 to 2024: `CAHPS_8` |
| `ACO_8` | Claims | 2016 to 2020: `ACO8` |
| `ACO_35` | Claims | 2016 to 2018: `ACO35` |
| `ACO_36` | Claims | 2016 to 2018: `ACO36` |
| `ACO_37` | Claims | 2016 to 2018: `ACO37` |
| `ACO_38` | Claims | 2016 to 2020: `ACO38` |
| `ACO_9` | Claims | 2016: `ACO9` |
| `ACO_10` | Claims | 2016: `ACO10` |
| `ACO_43` | Claims | 2017 to 2020: `ACO43` |
| `ACO_44` | Claims | 2017 to 2018: `ACO44` |
| `ACO_11` | EHR attestation | 2016 to 2018: `ACO11` |
| `ACO_12` | Web Interface | 2017 to 2018: `ACO12` |
| `ACO_39` | Web Interface | 2016: `ACO39` |
| `ACO_15` | Web Interface | 2016 to 2018: `ACO15` |
| `ACO_16` | Web Interface | 2016 to 2018: `ACO16` |
| `ACO_21` | Web Interface | 2016: `ACO21` |
| `ACO_30` | Web Interface | 2016 to 2018: `ACO30` |
| `ACO_31` | Web Interface | 2016: `ACO31` |
| `ACO_33` | Web Interface | 2016: `ACO33` |
| `ACO_41` | Web Interface | 2016 to 2018: `ACO41` |
| `DM_COMP` | Web Interface | 2016 to 2018: `DM_Comp` |
| `Q318` | Web Interface | 2016 to 2020: `ACO13`; 2021 to 2024: `QualityID_318` |
| `Q110` | Web Interface | 2016 to 2020: `ACO14`; 2021 to 2024: `QualityID_110` |
| `Q226` | Web Interface | 2016 to 2020: `ACO17`; 2021 to 2024: `QualityID_226` |
| `Q113` | Web Interface | 2016 to 2020: `ACO19`; 2021 to 2024: `QualityID_113` |
| `Q112` | Web Interface | 2016 to 2020: `ACO20`; 2021 to 2024: `QualityID_112` |
| `Q438` | Web Interface | 2016 to 2020: `ACO42`; 2021 to 2024: `QualityID_438` |
| `Q370` | Web Interface | 2016 to 2020: `ACO40`; 2021 to 2024: `QualityID_370` |
| `Q134` | Web Interface | 2016 to 2020: `ACO18`; 2021 to 2024: `QualityID_134_WI` |
| `Q134` | eCQM or MIPS CQM | 2021: `QualityID_134_eCQM-CQM` |
| `Q134` | eCQM | 2022 to 2024: `QualityID_134_eCQM` |
| `Q134` | MIPS CQM | 2022 to 2024: `QualityID_134_MIPSCQM` |
| `Q134` | Medicare CQM | 2024: `QualityID_134_MedicareCQM` |
| `Q001` | Web Interface | 2016 to 2020: `ACO27`; 2021 to 2024: `QualityID_001_WI` |
| `Q001` | eCQM or MIPS CQM | 2021: `QualityID_001_eCQM-CQM` |
| `Q001` | eCQM | 2022 to 2024: `QualityID_001_eCQM` |
| `Q001` | MIPS CQM | 2022 to 2024: `QualityID_001_MIPSCQM` |
| `Q001` | Medicare CQM | 2024: `QualityID_001_MedicareCQM` |
| `Q236` | Web Interface | 2016 to 2020: `ACO28`; 2021 to 2024: `QualityID_236_WI` |
| `Q236` | eCQM or MIPS CQM | 2021: `QualityID_236_eCQM-CQM` |
| `Q236` | eCQM | 2022 to 2024: `QualityID_236_eCQM` |
| `Q236` | MIPS CQM | 2022 to 2024: `QualityID_236_MIPSCQM` |
| `Q236` | Medicare CQM | 2024: `QualityID_236_MedicareCQM` |
| `Q479` | Claims | 2021 to 2024: `Measure_479` (times 100) |
| `MCC1` | Claims | 2021: `Measure_MCC1` |
| `Q484` | Claims | 2022 to 2024: `Measure_484` |

## County file columns

Header spelling changed four times while the column order stayed fixed. 2017 headers end in a tab, which the loader trims.

| canonical column | source by period |
|---|---|
| `file_year` | 2016 to 2018: `Year`; 2019 to 2019A: `year`; 2020 to 2024: `Year` |
| `aco_source_id` | 2016 to 2018: `ACO ID`; 2019 to 2019A: `aco_id`; 2020 to 2024: `ACO_ID` |
| `state_name` | 2016 to 2017: `State Name`; 2018: `State name`; 2019 to 2019A: `state_name`; 2020 to 2024: `State_Name` |
| `county_name` | 2016 to 2017: `County Name`; 2018: `County name`; 2019 to 2019A: `county_name`; 2020 to 2024: `County_Name` |
| `ssa_state_code` | 2016 to 2018: `State ID`; 2019 to 2019A: `state_id`; 2020 to 2024: `State_ID` |
| `ssa_county_code` | 2016 to 2018: `County ID`; 2019 to 2019A: `county_id`; 2020 to 2024: `County_ID` |
| `person_years_esrd` | 2016 to 2018: `ESRD assigned beneficiary person-years`; 2019 to 2019A: `ab_psn_yrs_esrd`; 2020 to 2024: `AB_Psn_Yrs_ESRD` |
| `person_years_disabled` | 2016 to 2018: `DISABLED assigned beneficiary person-years`; 2019 to 2019A: `ab_psn_yrs_dis`; 2020 to 2024: `AB_Psn_Yrs_DIS` |
| `person_years_aged_dual` | 2016 to 2018: `AGED/DUAL assigned beneficiary person-years`; 2019 to 2019A: `ab_psn_yrs_agdu`; 2020 to 2024: `AB_Psn_Yrs_AGDU` |
| `person_years_aged_nondual` | 2016 to 2018: `AGED/NON-DUAL assigned beneficiary person-years`; 2019 to 2019A: `ab_psn_yrs_agnd`; 2020 to 2024: `AB_Psn_Yrs_AGND` |
| `total_person_years` | 2016 to 2018: `Total assigned beneficiary person-years`; 2019 to 2019A: `tot_ab_psn_yrs`; 2020 to 2024: `Tot_AB_Psn_Yrs` |
| `total_assigned_beneficiaries` | 2016 to 2018: `Total assigned beneficiaries`; 2019 to 2019A: `tot_ab`; 2020 to 2024: `Tot_AB` |
