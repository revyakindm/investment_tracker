{{ config(
materialized='incremental',
unique_key=['bond_figi', 'planned_payment_date']
)
}}

with payments as (select c.bond_figi,
                         c.coupon_date,
                         cp.payment_date,
                         cp.amount
                  from {{ source('ods', 'coupons') }} c
                           join {{ source('ods', 'coupons_payments') }} cp
                                on c.bond_figi = cp.bond_figi and
                                   c.coupon_date between cp.payment_date - interval '7 days' and cp.payment_date)

select b.bond_figi, b.ticker, b.bond_name,
       c.coupon_date planned_payment_date, p.payment_date actual_payment_date,
       b.first_purchase_date,
       case when p.payment_date is not null then True else b.is_in_portfolio end is_in_portfolio,
       case when p.payment_date is null and b.is_in_portfolio = False then 'Нет. Не в портфеле'
            when p.payment_date >= c.coupon_date then 'Да'
            else 'Нет'
           end payment_status,
       p.amount,
       now() updated_at
from {{ source('ods', 'coupons') }} c
join {{ source('ods', 'bonds') }} b on b.bond_figi = c.bond_figi
left join payments p
    on c.bond_figi = p.bond_figi
           and c.coupon_date = p.coupon_date
where c.coupon_date between b.first_purchase_date and current_date
order by b.bond_figi, c.coupon_date