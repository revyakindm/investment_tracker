insert into mart.coupons_payments_status (bond_figi, ticker, bond_name, planned_payment_date, actual_payment_date,
first_purchase_date, is_in_portfolio, payment_status, payment_amount)

with last_payment_date as (select cp.bond_figi, max(payment_date) max_date
                           from ods.coupons_payments cp
                           group by cp.bond_figi),
     last_coupon as (select c.bond_figi, max(c.coupon_date) max_date
                     from ods.coupons c
                     where c.coupon_date < CURRENT_DATE
                     group by c.bond_figi)

select lc.bond_figi, ticker, bond_name,
       lc.max_date planned_payment_date,
       case when lpd.max_date < lc.max_date then null end actual_payment_date,
       first_purchase_date, is_in_portfolio,
       case when lpd.max_date is not null then 'Да'
            when lpd.max_date is null and lc.max_date < first_purchase_date then 'Нет. Куплено после последнего начисления'
            when lpd.max_date is null and b.is_in_portfolio is False then 'Нет. Не в портфеле'
            else 'Нет'
           end payment_status,
       cp.amount payment_amount
from last_coupon lc
         left join last_payment_date lpd
                   on lc.bond_figi = lpd.bond_figi
         left join ods.bonds b
                   on lc.bond_figi = b.bond_figi
         left join ods.coupons_payments cp
                   on lpd.bond_figi = cp.bond_figi and lpd.max_date = cp.payment_date
order by bond_name

on conflict (bond_figi, planned_payment_date) DO UPDATE SET
actual_payment_date = EXCLUDED.actual_payment_date,
payment_status = EXCLUDED.payment_status,
payment_amount = EXCLUDED.payment_amount,
updated_at = now()
where mart.coupons_payments_status.actual_payment_date is distinct from EXCLUDED.actual_payment_date
    or mart.coupons_payments_status.payment_status is distinct from EXCLUDED.payment_status
    or mart.coupons_payments_status.payment_amount is distinct from EXCLUDED.payment_amount