{{ config(
materialized='incremental',
unique_key=['bond_figi', 'planned_payment_date']
)
}}

with last_coupon_date as (select c.bond_figi, max(c.coupon_date) max_date
                          from {{ source('ods', 'coupons') }} c
                          where c.coupon_date < CURRENT_DATE
                          group by c.bond_figi)

select b.bond_figi, b.ticker, b.bond_name,
       lcd.max_date planned_payment_date, cp.payment_date actual_payment_date,
       first_purchase_date, is_in_portfolio,
       case when cp.payment_date is null and lcd.max_date < first_purchase_date then 'Нет. Куплена после даты выплаты'
            when cp.payment_date is null and is_in_portfolio = False then 'Нет. Не в портфеле'
           when cp.payment_date >= lcd.max_date then 'Да'
        else 'Нет'
        end payment_status,
        cp.amount,
        now() updated_at
from {{ source('ods', 'bonds') }} b
left join last_coupon_date lcd
    on b.bond_figi = lcd.bond_figi
left join {{ source('ods', 'coupons_payments') }} cp
    on lcd.bond_figi = cp.bond_figi and lcd.max_date <= cp.payment_date
order by bond_name