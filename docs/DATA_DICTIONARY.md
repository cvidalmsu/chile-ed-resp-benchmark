# Data dictionary

The authoritative machine-readable dictionary is `data_dictionary.csv`. All records are synthetic.

| Field | Type | Unit | Description |
|---|---|---|---|
| `record_id` | string | - | Unique synthetic site-week identifier. |
| `site_id` | string | - | Artificial hospital-site identifier. |
| `site_profile` | category | - | Synthetic operational profile. |
| `region_group` | category | - | Synthetic climate group; not an administrative region. |
| `sequence_index` | integer | week index | Chronological position within each site. |
| `year` | integer | year | Calendar year associated with epidemiological week. |
| `epi_week` | integer | week | Epidemiological week. |
| `week_start` | date | YYYY-MM-DD | Monday starting the epidemiological week. |
| `high_respiratory_infection` | integer | consultations | Primary synthetic forecasting target. |
| `influenza` | integer | consultations | Synthetic influenza consultations. |
| `pneumonia` | integer | consultations | Synthetic pneumonia consultations. |
| `bronchial_crisis` | integer | consultations | Synthetic bronchial-crisis consultations. |
| `other_respiratory` | integer | consultations | Synthetic other-respiratory consultations. |
| `covid19_identified` | integer | consultations | Synthetic identified COVID-19 consultations. |
| `covid19_unidentified` | integer | consultations | Synthetic unidentified COVID-19 consultations. |
| `respiratory_total` | integer | consultations | Sum of the seven cause-specific counts. |
| `age_lt1` | integer | consultations | Total respiratory consultations younger than one year. |
| `age_1_4` | integer | consultations | Total respiratory consultations aged 1--4 years. |
| `age_5_14` | integer | consultations | Total respiratory consultations aged 5--14 years. |
| `age_15_64` | integer | consultations | Total respiratory consultations aged 15--64 years. |
| `age_65_plus` | integer | consultations | Total respiratory consultations aged 65 years or older. |
| `mean_temperature_c` | float | degrees Celsius | Synthetic weekly mean temperature proxy. |
| `precipitation_mm` | float | millimetres | Synthetic weekly precipitation proxy. |
| `holiday_week` | binary | 0/1 | Indicates a week containing a selected public-holiday period. |
| `school_vacation_week` | binary | 0/1 | Indicates winter school-vacation weeks. |
| `outbreak_intensity` | float | index | Latent synthetic respiratory-outbreak intensity. |
| `data_quality_flag` | category | - | Quality interpretation for extreme values. |
| `recommended_split` | category | - | Chronological benchmark partition. |
| `is_synthetic` | binary | 0/1 | Mandatory indicator that no observation is real. |
| `generator_seed` | integer | - | Pseudorandom generator seed. |
| `dataset_version` | string | - | Semantic dataset release version. |
