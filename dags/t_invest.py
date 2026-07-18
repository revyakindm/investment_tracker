import os
from datetime import datetime, timezone, timedelta

import pandas as pd
from psycopg2 import sql

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', 30)

from dotenv import load_dotenv
from t_tech.invest import Client
from t_tech.invest.schemas import InstrumentIdType

import psycopg2
from psycopg2.extras import execute_values

from pathlib import Path

load_dotenv()

TOKEN = os.getenv("T_INVEST_TOKEN")
HOST=os.getenv("POSTGRES_HOST")
PORT=os.getenv("POSTGRES_PORT")
DB=os.getenv("POSTGRES_DB")
USER=os.getenv("POSTGRES_USER")
PASSWORD=os.getenv("POSTGRES_PASSWORD")

TODAY = datetime.now(timezone.utc)
YEAR_2025 = datetime(2025, 1, 1, tzinfo=timezone.utc)

class DatabaseManage:
    def __init__(self, host, port, database, user, password, autocommit=False):
        self.connection = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
        )
        if autocommit:
            self.connection.autocommit = True

        self.cursor = self.connection.cursor()

    def select(self, query, how_many_lines=None, params=None):
        self.cursor.execute(query, params)
        if how_many_lines == 'all':
            results = self.cursor.fetchall()
        elif how_many_lines == 'one':
            results = self.cursor.fetchone()
        else:
            results = self.cursor.fetchone()

        return results

    def insert(self, query):
        self.cursor.execute(query)
        if not self.connection.autocommit:
            self.connection.commit()

    def insert_many(self, table_name, schema, data, conflict_col=None):
        if not data:
            return
        cols = list(data[0].keys())
        cols_rows = ', '.join(cols)
        val = [tuple(dct[c] for c in cols) for dct in data]
        if conflict_col:
            # conflict_col может быть строкой или списком
            if isinstance(conflict_col, (list, tuple)):
                conflict_str = ', '.join(conflict_col)
                update_cols = ', '.join(f"{c} = EXCLUDED.{c}" for c in cols if c not in conflict_col)
            else:
                conflict_str = conflict_col
                update_cols = ', '.join(f"{c} = EXCLUDED.{c}" for c in cols if c != conflict_col)
            query = f"""
                insert into {schema}.{table_name} ({cols_rows})
                values %s
                on conflict ({conflict_str}) do update set {update_cols}
            """
        else:
            query = f"insert into {schema}.{table_name} ({cols_rows}) values %s"
        execute_values(self.cursor, query, val)

def _parse_money_value(mv):
    if mv is not None:
        return mv.units + mv.nano / 1e9
    else:
        return mv

db = DatabaseManage(HOST, PORT, DB, USER, PASSWORD, autocommit=True)

with Client(TOKEN) as client:
        # Загружаю инфо по брокерскому счету
        accounts = client.users.get_accounts().accounts
        broker_account_info = [acc for acc in accounts if acc.type == 1][0].__dict__

        # выгружаю все figi облигаций, которые когда-то были с 2025 года
        all_operations = client.operations.get_operations(
            account_id=broker_account_info['id'],
            from_=YEAR_2025,
            to=TODAY,
        ).operations
        ever_bought_figis = {op.figi for op in all_operations if op.type == 'Покупка ценных бумаг'
                             and op.instrument_type == 'bond'}

        # максимальная дата в ods.coupons_payments
        max_date_payments = db.select("select max(payment_date) from ods.coupons_payments", 'one')
        date_payments_from = max_date_payments[0] if max_date_payments and max_date_payments[0] else YEAR_2025.date()

        # выплаты по облигациям
        coupon_payments = []
        for op in all_operations:
            temp_dct = {}
            if op.type == 'Выплата купонов' and op.instrument_type == 'bond' and op.date.date() > date_payments_from:
                temp_dct['operation_id'] = op.id
                temp_dct['bond_figi'] = op.figi
                temp_dct['payment_date'] = op.date.date()
                temp_dct['amount'] = _parse_money_value(op.payment)
                temp_dct['currency'] = op.currency
                coupon_payments.append(temp_dct)

        # облигации в портфеле на текущий момент
        bonds_figi_in_portfolio = {pos.figi for pos in client.operations.get_portfolio(account_id=broker_account_info['id']).positions\
                             if pos.instrument_type == 'bond'}

        # первая покупка каждой облигации
        bond_first_purchase = {}
        for op in all_operations:
            if op.type == 'Покупка ценных бумаг' and op.instrument_type == 'bond':
                bond_first_purchase.setdefault(op.figi, []).append(op.date)

        figi_in_db = db.select("select distinct bond_figi from ods.bonds", how_many_lines='all')
        if figi_in_db:
            figi_in_db_lst = [figi[0] for figi in figi_in_db]
        else:
            figi_in_db_lst = []

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
            coupon = client.instruments.get_bond_coupons(instrument_id=figi,
                                                         from_=datetime(2000, 1, 1, tzinfo=timezone.utc),
                                                         to=bond.maturity_date).events
            if figi not in figi_in_db_lst:
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
                temp_dct_portfolio['bond_figi'] = pos.figi
                temp_dct_portfolio['quantity'] = _parse_money_value(pos.quantity)
                temp_dct_portfolio['average_price'] = _parse_money_value(pos.average_position_price)
                temp_dct_portfolio['current_nkd'] = _parse_money_value(pos.current_nkd)
                temp_dct_portfolio['expected_yield'] = _parse_money_value(pos.expected_yield)
                temp_dct_portfolio['current_price'] = _parse_money_value(pos.current_price)
                temp_dct_portfolio['snapshot_date'] = TODAY.date()
                my_portfolio.append(temp_dct_portfolio)

db.insert_many('bonds', 'ods', bonds, conflict_col='bond_figi')
db.insert_many('coupons', 'ods', coupons)
db.insert_many('portfolio_snapshots', 'ods', my_portfolio, conflict_col=['snapshot_date', 'bond_figi'])
db.insert_many('coupons_payments', 'ods', coupon_payments)

SQL_FILE = Path(__file__).parent.parent / "sql" / "query_coupons_payments_status.sql"
db.insert(SQL_FILE.read_text(encoding="utf-8"))