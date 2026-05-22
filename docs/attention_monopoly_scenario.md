# Attention Monopoly Scenario

Сценарий описывает перераспределение капитала и ВДС, когда единый AI-ассистент становится основной поверхностью доступа к пользователю.

## 1. Формализация

Для отрасли $s$:

$$
D_s \in [0,1] \quad \text{attention dependency},
\qquad
I_s \in [0,1] \quad \text{platform integration capacity},
\qquad
m_s \quad \text{platform markup}.
$$

Композитный риск:

$$
R_s = 100\left(
w_D D_s + w_I I_s + w_m \frac{m_s}{\max_j m_j} + w_E E_s + w_G G_s + w_A A_s(2035)
\right).
$$

Сдвиг ВДС:

$$
\Delta VA_s^{att} =
VA_s \bar A D_s I_s c_s \rho
- VA_s \bar A D_s m_s (1-I_s) \frac{1+E_s}{2}
+ \mathbf{1}_{s \in platform}\Omega,
$$

где $E_s$ — vulnerable SME share, $G_s$ — gatekeeping exposure, $c_s$ — CAC saving midpoint, $\bar A=0.4$ — base saturation доля AI-интерфейса, $\rho=0.5$ — retained CAC saving, $\Omega$ — доля платформенной ренты, направленная в IT/platform sector.

## 2. Highest Risk Sectors

| sector_id | sector_name_ru | attention_dependency | integration_capacity | platform_markup_mid | vulnerable_sme_share | gatekeeping_exposure | attention_risk_score |
| --- | --- | --- | --- | --- | --- | --- | --- |
| J | ИТ и связь | 0.900 | 0.900 | 0.180 | 0.200 | 0.800 | 79.653 |
| G_nonfood | Торговля (не еда) | 0.900 | 0.850 | 0.120 | 0.800 | 0.850 | 78.834 |
| M | Профессиональные и научные услуги | 0.700 | 0.550 | 0.220 | 0.650 | 0.700 | 71.880 |
| K | Финансы и страхование | 0.850 | 0.650 | 0.060 | 0.450 | 0.900 | 69.471 |
| G_food | Торговля (еда) | 0.780 | 0.820 | 0.070 | 0.450 | 0.700 | 64.725 |
| H | Транспорт и логистика | 0.450 | 0.450 | 0.120 | 0.550 | 0.550 | 47.748 |
| C | Обрабатывающая промышленность без машиностроения | 0.350 | 0.300 | 0.080 | 0.450 | 0.350 | 35.106 |
| C_mach | Машиностроение (ОКВЭД 26–30) | 0.250 | 0.500 | 0.060 | 0.350 | 0.300 | 32.743 |
| DE | Энергетика и ЖКХ | 0.300 | 0.250 | 0.050 | 0.300 | 0.450 | 31.061 |
| F | Строительство | 0.200 | 0.200 | 0.080 | 0.550 | 0.250 | 26.521 |

## 3. Net GVA Shift

| sector_id | sector_name_ru | platform_access_fee_bn_rub | cac_saving_va_gain_bn_rub | attention_gva_shift_bn_rub | capital_reallocation_pressure_bn_rub |
| --- | --- | --- | --- | --- | --- |
| C | Обрабатывающая промышленность без машиностроения | 120.481 | 35.610 | -84.871 | 156.091 |
| M | Профессиональные и научные услуги | 206.458 | 125.126 | -81.332 | 331.585 |
| H | Транспорт и логистика | 114.938 | 50.559 | -64.379 | 165.497 |
| F | Строительство | 37.084 | 5.981 | -31.103 | 43.065 |
| B | Добыча полезных ископаемых | 22.904 | 3.368 | -19.536 | 26.272 |
| DE | Энергетика и ЖКХ | 14.241 | 3.652 | -10.590 | 17.893 |
| C_mach | Машиностроение (ОКВЭД 26–30) | 11.420 | 9.869 | -1.551 | 21.290 |
| G_food | Торговля (еда) | 18.934 | 152.968 | 134.034 | 171.903 |
| K | Финансы и страхование | 47.677 | 203.548 | 155.871 | 251.226 |
| G_nonfood | Торговля (не еда) | 90.403 | 664.074 | 573.671 | 754.478 |

## 4. Deadweight Loss

| sector_id | sector_name_ru | platform_markup_mid | attention_dependency | deadweight_loss_bn_rub |
| --- | --- | --- | --- | --- |
| M | Профессиональные и научные услуги | 0.220 | 0.700 | 54.752 |
| J | ИТ и связь | 0.180 | 0.900 | 32.282 |
| G_nonfood | Торговля (не еда) | 0.120 | 0.900 | 27.121 |
| H | Транспорт и логистика | 0.120 | 0.450 | 10.921 |
| C | Обрабатывающая промышленность без машиностроения | 0.080 | 0.350 | 4.451 |
| G_food | Торговля (еда) | 0.070 | 0.780 | 1.990 |
| K | Финансы и страхование | 0.060 | 0.850 | 1.691 |
| F | Строительство | 0.080 | 0.200 | 1.121 |
| C_mach | Машиностроение (ОКВЭД 26–30) | 0.060 | 0.250 | 0.305 |
| B | Добыча полезных ископаемых | 0.050 | 0.100 | 0.216 |

## 5. Artifacts

- `output/attention_monopoly_risk_gradient.png`
- `output/attention_monopoly_gva_shift.png`
- `output/attention_abm_dynamics.png`
- `output/attention_deadweight_loss.png`
- `output/reports/attention_monopoly_scenario_report_ru.pdf`
- `data/benchmarks_attention_monopoly.csv`
- `data/processed/attention_monopoly_sector_summary.csv`
