insert into mart.coupons_payments_status (bond_figi, ticker, bond_name, planned_payment_date, actual_payment_date,
first_purchase_date, is_in_portfolio, payment_status, amount)

with payments as (select c.bond_figi,
                         c.coupon_date,
                         cp.payment_date,
                         cp.amount
                  from ods.coupons c
                           join ods.coupons_payments cp
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
       p.amount
from ods.coupons c
join ods.bonds b on b.bond_figi = c.bond_figi
left join payments p
    on c.bond_figi = p.bond_figi
           and c.coupon_date = p.coupon_date
where c.coupon_date between b.first_purchase_date and current_date
order by b.bond_figi, c.coupon_date

on conflict (bond_figi, planned_payment_date) DO UPDATE SET
actual_payment_date = EXCLUDED.actual_payment_date,
payment_status = EXCLUDED.payment_status,
amount = EXCLUDED.amount,
updated_at = now()
where mart.coupons_payments_status.actual_payment_date is distinct from EXCLUDED.actual_payment_date
    or mart.coupons_payments_status.payment_status is distinct from EXCLUDED.payment_status
    or mart.coupons_payments_status.amount is distinct from EXCLUDED.amount
