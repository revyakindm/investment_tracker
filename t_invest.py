import os
from datetime import datetime, timezone, timedelta

import pandas as pd
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', 30)

from dotenv import load_dotenv
from t_tech.invest import Client
from t_tech.invest.schemas import InstrumentIdType

import json

load_dotenv()

TOKEN = os.getenv("T_INVEST_TOKEN")

today = datetime.now(timezone.utc)
year_2025 = datetime(2025, 1, 1, tzinfo=timezone.utc)

# instruments, operations, users

def _parse_money_value(mv):
    if mv is not None:
        return mv.units + mv.nano / 1e9
    else:
        return mv

with Client(TOKEN) as client:
        # составляю все поля для каждой таблицы
        bonds_columns = ['figi', 'ticker', 'instrument_uid', 'instrument_type', 'bond_type', 'bond_name', 'nominal',
                         'currency', 'sector', 'maturity_date', 'coupon_quantity_per_year', 'first_purchase_date',
                         'is_in_portfolio', 'created_at_utc', 'updated_at_utc']

        coupon_columns = ['bond_figi', 'coupon_date', 'coupon_type', 'pay_per_bond']

        portfolio_columns = ['snapshot_date', 'bond_figi', 'quantity', 'average_price', 'current_nkd',
                             'expected_yield', 'current_price']

        # Загружаю инфо по брокерскому счету
        accounts = client.users.get_accounts().accounts
        broker_account_info = [acc for acc in accounts if acc.type == 1][0].__dict__

        # Все позиции в портфеле
        # important_columns_positions = ['ticker', 'instrument_uid', 'figi', 'instrument_type', 'quantity', 'quantity_lots',
        #                      'average_position_price', 'expected_yield', 'current_nkd', 'current_price']

        # выгружаю все figi облигаций, которые когда-то были с 2025 года
        all_operations = client.operations.get_operations(
            account_id=broker_account_info['id'],
            from_=year_2025,
            to=today,
        ).operations
        ever_bought_figis = {op.figi for op in all_operations if op.type == 'Покупка ценных бумаг'
                             and op.instrument_type == 'bond'}

        # облигации в портфеле на текущий момент
        bonds_figi_in_portfolio = {pos.figi for pos in client.operations.get_portfolio(account_id=broker_account_info['id']).positions\
                             if pos.instrument_type == 'bond'}

        # первая покупка каждой облигации
        bond_first_purchase = {}
        for op in all_operations:
            if op.type == 'Покупка ценных бумаг' and op.instrument_type == 'bond':
                bond_first_purchase.setdefault(op.figi, []).append(op.date)

        bonds = []
        coupons = []
        for figi in ever_bought_figis:
            # формирую инфо по облигациям
            temp_dct_bonds_info = {}
            bond = client.instruments.bond_by(
                id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                id=figi
            ).instrument
            temp_dct_bonds_info['bond_figi'] = bond.figi
            temp_dct_bonds_info['ticker'] = bond.ticker
            temp_dct_bonds_info['instrument_uid'] = bond.uid
            temp_dct_bonds_info['instrument_type'] = 'bond'
            temp_dct_bonds_info['bond_type'] = bond.bond_type.name
            temp_dct_bonds_info['bond_name'] = bond.name
            temp_dct_bonds_info['nominal'] = _parse_money_value(bond.nominal)
            temp_dct_bonds_info['currency'] = bond.currency
            temp_dct_bonds_info['sector'] = bond.sector
            temp_dct_bonds_info['maturity_date'] = bond.maturity_date.date()
            temp_dct_bonds_info['coupon_quantity_per_year'] = bond.coupon_quantity_per_year
            temp_dct_bonds_info['first_purchase_date'] = min(bond_first_purchase[figi]).date()
            temp_dct_bonds_info['is_in_portfolio'] = True if figi in bonds_figi_in_portfolio else False

            bonds.append(temp_dct_bonds_info)

            # формирую инфо по купонам
            coupon = client.instruments.get_bond_coupons(instrument_id=figi).events
            for coup in coupon:
                temp_dct_coupon_info = {}
                temp_dct_coupon_info['bond_figi'] = coup.figi
                temp_dct_coupon_info['coupon_date'] = coup.coupon_date.date()
                temp_dct_coupon_info['coupon_type'] = coup.coupon_type.name
                temp_dct_coupon_info['pay_one_bond'] = _parse_money_value(coup.pay_one_bond)
                coupons.append(temp_dct_coupon_info)

        # текущее состояние портфеля
        current_positions = client.operations.get_portfolio(account_id=broker_account_info['id']).positions
        my_portfolio = []
        for pos in current_positions:
            if pos.instrument_type == 'bond':
                temp_dct_portfolio = {}
                temp_dct_portfolio['snapshot_date'] = today.date()
                temp_dct_portfolio['bond_figi'] = pos.figi
                temp_dct_portfolio['quantity'] = _parse_money_value(pos.quantity)
                temp_dct_portfolio['average_price'] = _parse_money_value(pos.average_position_price)
                temp_dct_portfolio['current_nkd'] = _parse_money_value(pos.current_nkd)
                temp_dct_portfolio['expected_yield'] = _parse_money_value(pos.expected_yield)
                temp_dct_portfolio['current_price'] = _parse_money_value(pos.current_price)
                my_portfolio.append(temp_dct_portfolio)

        print(bonds, coupons, my_portfolio, sep='\n\n')