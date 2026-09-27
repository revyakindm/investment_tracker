create schema stg;
create schema ods;
create schema mart;

create table stg.bonds (
	bond_figi TEXT primary key,
	ticker TEXT,
	instrument_uid text,
	instrument_type text,
	bond_type text,
	bond_name text,
	nominal numeric(18, 4),
	currency TEXT,
	sector TEXT,
	maturity_date DATE,
	coupon_quantity_per_year smallint,
	first_purchase_date DATE,
	is_in_portfolio BOOLEAN,
	created_at_utc TIMESTAMPTZ default now(),
	updated_at_utc TIMESTAMPTZ default now()
);

create table stg.coupons (
	bond_figi TEXT,
	coupon_date date,
	coupon_type text,
	pay_one_bond numeric(18, 4),
	primary key (bond_figi, coupon_date)
);

create table stg.portfolio_snapshots (
	snapshot_date date not null,
	bond_figi text,
	quantity numeric(18, 4),
	average_price numeric(18, 4),
	current_nkd numeric(18, 4),
	expected_yield numeric(18, 4),
	current_price numeric(18, 4),
	primary key (snapshot_date, bond_figi)
);

create table stg.coupons_payments (
    operation_id bigint,
    bond_figi text not null,
    payment_date date not null,
    amount numeric(18, 4) not null,
    currency text not null,
    loaded_at timestamp not null default now(),
    primary key (operation_id)
);

create table ods.bonds (
	bond_figi TEXT primary key,
	ticker TEXT,
	instrument_uid text,
	instrument_type text,
	bond_type text,
	bond_name text,
	nominal numeric(18, 4),
	currency TEXT,
	sector TEXT,
	maturity_date DATE,
	coupon_quantity_per_year smallint,
	first_purchase_date DATE,
	is_in_portfolio BOOLEAN,
	created_at_utc TIMESTAMPTZ default now(),
	updated_at_utc TIMESTAMPTZ default now()
);

create table ods.coupons (
	bond_figi TEXT references ods.bonds(bond_figi) on delete restrict,
	coupon_date date,
	coupon_type text,
	pay_one_bond numeric(18, 4),
	primary key (bond_figi, coupon_date)
);

create table ods.portfolio_snapshots (
	snapshot_date date not null,
	bond_figi text references ods.bonds(bond_figi) on delete restrict,
	quantity numeric(18, 4),
	average_price numeric(18, 4),
	current_nkd numeric(18, 4),
	expected_yield numeric(18, 4),
	current_price numeric(18, 4),
	primary key (snapshot_date, bond_figi)
);

create table ods.coupons_payments (
    operation_id bigint,
    bond_figi text not null references ods.bonds(bond_figi),
    payment_date date not null,
    amount numeric(18, 4) not null,
    currency text not null,
    loaded_at timestamp not null default now(),
    primary key (operation_id)
);
