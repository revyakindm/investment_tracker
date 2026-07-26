from datetime import datetime, timezone, timedelta

from t_tech.invest import Client
from t_tech.invest.schemas import InstrumentIdType

import psycopg2
from psycopg2.extras import execute_values

from pathlib import Path

from airflow import DAG
from airflow.hooks.base import BaseHook
from airflow.decorators import task

import logging
log = logging.getLogger("airflow.task")


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

    def select(self, query):
        self.cursor.execute(query)
        self.connection.commit()

    def fetch(self, query, how_many_lines=None, params=None):
        self.cursor.execute(query, params)
        columns = [col[0] for col in self.cursor.description]
        if how_many_lines == 'all':
            rows = self.cursor.fetchall()
        else:
            rows = self.cursor.fetchone()

        return rows, columns

    def insert_many(self, table, schema, data=None, conflict_col=None, columns=None, val=None):
        if columns is not None and val is not None:
            _columns = columns
            _columns_rows = ', '.join(_columns)
        else:
            if not data:
                return
            _columns = list(data[0].keys())
            _columns_rows = ', '.join(_columns)
            val = [tuple(dct[col] for col in _columns) for dct in data]
        if conflict_col:
            if isinstance(conflict_col, (list, tuple)):
                conflict_str = ', '.join(conflict_col)
                update_columns = ', '.join([f'{col} = EXCLUDED.{col}' for col in _columns if col not in conflict_col])
            else:
                conflict_str = conflict_col
                update_columns = ', '.join([f'{col} = EXCLUDED.{col}' for col in _columns if col != conflict_col])
            query = f"""insert into {schema}.{table} ({_columns_rows})
                        values %s
                        on conflict ({conflict_str}) do update set {update_columns}"""
        else:
            query = f"""insert into {schema}.{table} ({_columns_rows}) values %s"""

        execute_values(self.cursor, query, val)

def _parse_money_value(mv):
    if mv is not None:
        return mv.units + mv.nano / 1e9
    else:
        return mv

def _db():
    config_local_db = BaseHook.get_connection("local_db_postgres")
    return DatabaseManage(
        config_local_db.host, config_local_db.port,
        config_local_db.schema,
        config_local_db.login, config_local_db.password,
        autocommit=True
    )

@task
def from_api_to_stg(**context):
    config_t_invest = BaseHook.get_connection("t_invest_token")
    token = config_t_invest.password

    today = context['data_interval_end']

    db = _db()

    try:
        with Client(token) as client:
                # Загружаю инфо по брокерскому счету
                accounts = client.users.get_accounts().accounts
                broker_account_info = [acc for acc in accounts if acc.type == 1][0].__dict__

                # выгружаю все figi облигаций, которые когда-то были с 2025 года
                all_operations = client.operations.get_operations(
                    account_id=broker_account_info['id'],
                    from_=YEAR_2025,
                    to=today,
                ).operations
                ever_bought_figis = {op.figi for op in all_operations if op.type == 'Покупка ценных бумаг'
                                     and op.instrument_type == 'bond'}

                # максимальная дата в ods.coupons_payments
                row, _ = db.fetch("select max(payment_date) from ods.coupons_payments")
                date_payments_from = row[0] if row and row[0] else YEAR_2025.date()

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

                figi_in_db, _ = db.fetch("select distinct bond_figi from ods.bonds", how_many_lines='all')
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
                        temp_dct_portfolio['snapshot_date'] = today.date()
                        my_portfolio.append(temp_dct_portfolio)

        db.cursor.execute('''truncate table stg.bonds, stg.coupons, stg.portfolio_snapshots, stg.coupons_payments cascade''')

        db.insert_many('bonds', 'stg', bonds, conflict_col='bond_figi')
        db.insert_many('coupons', 'stg', coupons)
        db.insert_many('portfolio_snapshots', 'stg', my_portfolio, conflict_col=['snapshot_date', 'bond_figi'])

        log.info(f"coupon_payments count: {len(coupon_payments)}")
        log.info(f"coupon_payments content: {coupon_payments}")
        log.info(f"autocommit: {db.connection.autocommit}")
        db.insert_many('coupons_payments', 'stg', coupon_payments)
    finally:
        db.connection.close()

@task
def bonds_from_stg_to_ods():
    db = _db()
    try:
        q = """select * from stg.bonds"""
        rows, columns = db.fetch(q, 'all')
        db.insert_many('bonds', 'ods',None,'bond_figi', columns, rows)
    finally:
        db.connection.close()

@task
def remaining_tables_to_ods():
    db = _db()
    try:
        q_coupons = """select * from stg.coupons"""
        q_portfolio_snapshots = """select * from stg.portfolio_snapshots"""
        q_coupons_payments = """select * from stg.coupons_payments"""

        rows_coupons, columns_coupons = db.fetch(q_coupons, 'all')
        rows_portfolio_snapshots, columns_portfolio_snapshots = db.fetch(q_portfolio_snapshots, 'all')
        rows_coupons_payments, columns_coupons_payments = db.fetch(q_coupons_payments, 'all')

        db.insert_many('coupons', 'ods',None,['bond_figi', 'coupon_date'], columns_coupons, rows_coupons)
        db.insert_many('portfolio_snapshots', 'ods', None, ['snapshot_date', 'bond_figi'],
                       columns_portfolio_snapshots, rows_portfolio_snapshots)
        db.insert_many('coupons_payments', 'ods', None, 'operation_id', columns_coupons_payments, rows_coupons_payments)
    finally:
        db.connection.close()

@task
def update_coupons_payments_status():
    db = _db()
    try:
        SQL_FILE = Path(__file__).parent.parent / "sql" / "query_coupons_payments_status.sql"
        db.select(SQL_FILE.read_text(encoding="utf-8"))
    finally:
        db.connection.close()

@task
def start():
    pass

@task
def end():
    pass

default_args = {
    "owner": "revyakindm",
    "start_date": datetime(2026, 7, 19),
    "retries": 1,
    "retry_delay": timedelta(seconds=30)
}

with DAG(
    dag_id="investment_tracker",
    schedule="@daily",
    default_args=default_args,
    catchup=False,
    max_active_runs=1,
) as dag:
    (
            start()
            >> from_api_to_stg()
            >> bonds_from_stg_to_ods()
            >> remaining_tables_to_ods()
            >> update_coupons_payments_status()
            >> end()
    )