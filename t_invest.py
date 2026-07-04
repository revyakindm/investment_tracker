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

        # формирую словарь с облигациями
        figi_in_portfolio = [pos.figi for pos in client.operations.get_portfolio(account_id=broker_account_info['id']).positions]
        bonds = {}
        for figi in ever_bought_figis:
            temp_dct = {}
            bond = client.instruments.bond_by(
                id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_FIGI,
                id=figi
            ).instrument
            temp_dct['figi'] = bond.figi
            temp_dct['ticker'] = bond.ticker
            temp_dct['instrument_uid'] = bond.uid
            temp_dct['instrument_type'] = 'bond'
            temp_dct['bond_type'] = bond.bond_type.name
            temp_dct['bond_name'] = bond.name
            temp_dct['nominal'] = bond.nominal
            temp_dct['currency'] = bond.currency
            temp_dct['sector'] = bond.sector
            temp_dct['maturity_date'] = bond.maturity_date
            temp_dct['coupon_quantity_per_year'] = bond.coupon_quantity_per_year

            # first_purchase_date
            bond_first_purchase = {}
            for op in all_operations:
                if op.type == 'Покупка ценных бумаг' and op.instrument_type == 'bond' and op.operation_type.OPERATION_TYPE_BUY == 15:
                    bond_first_purchase.setdefault(temp_dct['figi'], []).append(op.date)
            temp_dct['first_purchase_date'] = min(bond_first_purchase[temp_dct['figi']]).date()

            # is_in_porfolio
            temp_dct['is_in_portfolio'] = True if figi in figi_in_portfolio else False

            bonds[figi] = temp_dct
        print(bonds)

        # for pos in client.operations.get_portfolio(account_id=broker_account_info['id']).positions:
        #     print(pos.__dict__)
        #     break
            # if pos.instrument_type == 'bond':
            #     temp_dct = {}
            #
            #     # figi, ticker, instrument_uid, instrument_type
            #     for col in bonds_columns:
            #         if pos.__dict__.get(col) is not None:
            #             temp_dct[col] = pos.__dict__.get(col)
            #
            #     # name
            #     temp_dct['bond_name'] = client.instruments.get_instrument_by(id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID, id=temp_dct['instrument_uid']).instrument.name
            #
            #     # nominal, currency, sector, maturity_date, coupon_quantity_per_year
            #     coupon_info = client.instruments.bond_by(id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID,id=temp_dct['instrument_uid']).instrument
            #     temp_dct['nominal'] = coupon_info.nominal
            #     temp_dct['currency'] = coupon_info.currency
            #     temp_dct['sector'] = coupon_info.sector
            #     temp_dct['maturity_date'] = coupon_info.maturity_date
            #     temp_dct['coupon_quantity_per_year'] = coupon_info.coupon_quantity_per_year
            #
            #     # first_purchase_date
            #     bond_first_purchase = {}
            #     bond_operations = client.operations.get_operations(
            #         account_id=broker_account_info['id'],  # ID счёта (обязательно)
            #         from_=year_2025,  # с какой даты
            #         to=today,  # по какую дату
            #         figi=temp_dct['figi']  # figi конкретного инструмента
            #     ).operations
            #     for op in bond_operations:
            #         if op.type == 'Покупка ценных бумаг' and op.operation_type.OPERATION_TYPE_BUY == 15:
            #             bond_first_purchase.setdefault(temp_dct['figi'], []).append(op.date)
            #     temp_dct['first_purchase_date'] = min(bond_first_purchase[temp_dct['figi']]).date()
            #
            #     # is_in_porfolio
            #     if
            #     if temp_dct['figi'] in ever_bought_figis:
            #         temp_dct['is_in_porfolio'] = temp_dct['figi']
            #
            #
            #     bonds[pos.figi] = temp_dct

            # break
        # print(bonds)
        # positions_list = client.operations.get_portfolio(account_id=broker_account_info['id']).positions
        # my_positions = [{col: getattr(pos, col, None) for col in important_columns_positions} for pos in positions_list]

        # Достаю названия позиций в портфеле
        # instruments_uids = [x['instrument_uid'] for x in my_positions]
        # positions_names = {}
        # for uid in instruments_uids:
        #         positions_names[uid] = client.instruments\
        #                                 .get_instrument_by(id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID
        #                                                    , id=uid).instrument.name
        #
        # # Кладу названия в словарь с позициями
        # for pos in my_positions:
        #         pos['name'] = positions_names.get(pos['instrument_uid'])
        #
        #
        # # a = client.instruments.get_bond_coupons(instrument_id='93d49733-cde2-4832-afd7-2274b4dcd96e').events # облигация floating
        # # print(a)#a.pay_one_bond, a.coupon_type, a.coupon_date)
        #
        # # Облигации
        # # Купонов в год, дата погашения, номинал, сектор, валюта
        # # ========================================================
        # # Купоны
        # # Дата ближайшего купона, тип купона, сумма купона
        # # Дата предыдущего купона, тип купона, сумма купона
        #
        # bonds_uids = [x['instrument_uid'] for x in my_positions if x['instrument_type'] == 'bond']
        # bonds_and_coupons_info = {}
        # for b in bonds_uids:
        #         # Облигации
        #         bond = client.instruments.bond_by(id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID,
        #                                          id=b).instrument
        #         # Купоны. Следующий и предыдущий
        #         next_coupon = None
        #         for nc in client.instruments.get_bond_coupons(instrument_id=b).events:
        #                 if nc.coupon_date < today:
        #                         continue
        #                 if next_coupon is None or nc.coupon_date < next_coupon.coupon_date:
        #                         next_coupon = nc
        #
        #         previous_coupon = None
        #         for pc in client.instruments.get_bond_coupons(instrument_id=b).events:
        #                 if pc.coupon_date > today:
        #                         continue
        #                 if previous_coupon is None or pc.coupon_date > previous_coupon.coupon_date:
        #                         previous_coupon = pc
        #
        #         def _parse_money_value(mv):
        #             if mv is not None:
        #                 return mv.units + mv.nano / 1e9
        #             else:
        #                 return mv
        #
        #         # Добавляю информацию в словарь об облигациях и купонах
        #         bond_and_coupons_data = {
        #             'bond_figi': bond.figi,
        #             'bond_ticker': bond.ticker,
        #             'coupon_quantity_per_year': bond.coupon_quantity_per_year,
        #             'maturity_date': bond.maturity_date.date(),
        #             'nominal': _parse_money_value(bond.nominal),
        #             'sector': bond.sector,
        #             'currency': bond.currency,
        #             'next_coupon_date': next_coupon.coupon_date.date() if next_coupon else None,
        #             'next_pay_one_bond': _parse_money_value(next_coupon.pay_one_bond if next_coupon else None),
        #             'next_coupon_type': next_coupon.coupon_type.name if next_coupon else None,
        #             'previous_coupon_date': previous_coupon.coupon_date.date() if previous_coupon else None,
        #             'previous_pay_one_bond': _parse_money_value(previous_coupon.pay_one_bond if previous_coupon
        #                                                         else None),
        #             'previous_coupon_type': previous_coupon.coupon_type.name if previous_coupon else None
        #         }
        #         bonds_and_coupons_info[bond.figi] = bond_and_coupons_data
        #
        # # Дата первой покупки облигаций
        # bond_first_purchase = {}
        # for figi in bonds_and_coupons_info:
        #     bond_operations = client.operations.get_operations(
        #         account_id=broker_account_info['id'],  # ID счёта (обязательно)
        #         from_=year_2025,  # с какой даты
        #         to=today,  # по какую дату
        #         figi=bonds_and_coupons_info[figi]['bond_figi']  # figi конкретного инструмента
        #     ).operations
        #     for op in bond_operations:
        #         if op.type == 'Покупка ценных бумаг' and op.operation_type.OPERATION_TYPE_BUY == 15:
        #             bond_first_purchase.setdefault(figi, []).append(op.date)
        #     bond_first_purchase[figi] = min(bond_first_purchase[figi]).date()
        # # print(bond_first_purchase['BBG01MVSHPP3'])
        #
        # # Создаю/обновляю json с датами первых покупок облигаций
        # json_path = r'C:/Users/Дмитрий/Desktop/investment_tracker/bond_first_purchase.json'
        # if os.path.exists(json_path):
        #     with open(json_path, 'r') as f:
        #         json_data = json.load(f)
        #
        #     for k, v in bond_first_purchase.items():
        #         if k not in json_data:
        #             json_data[k] = v
        #
        #     with open(json_path, 'w', encoding='utf-8') as f:
        #         json.dump(json_data, f, indent=4, ensure_ascii=False, default=str)
        # else:
        #     with open(json_path, 'w', encoding='utf-8') as f:
        #         json.dump(bond_first_purchase, f, indent=4, ensure_ascii=False, default=str)
        #
        # # Добавляю в инфо об облигациях и купонах даты первых покупок и должна ли была пройти выплата
        # with open(json_path, 'r') as f:
        #     json_data = json.load(f)
        #
        # for figi, dat in json_data.items():
        #     # Даты первых покупок
        #     dat = datetime.strptime(dat, '%Y-%m-%d').date()
        #     bonds_and_coupons_info[figi]['first_purchase_date'] = dat
        #
        #     # Должна ли быть выплата по предыдущему купону
        #     diff_days = (bonds_and_coupons_info[figi]['previous_coupon_date'] - dat).days\
        #         if bonds_and_coupons_info[figi]['previous_coupon_date'] else None
        #     bonds_and_coupons_info[figi]['should_be_paid'] = 0 if diff_days is None or diff_days < 1 else 1
        #
        # # Были ли выплата в течение 7 дней после назначенной даты
        # for figi in bonds_and_coupons_info:
        #     # По-умолчанию проставляю у всех 0
        #     bonds_and_coupons_info[figi]['paid_amount'] = 0
        #
        #     # Если предыдущая выплата существовала, то указываю, сколько было выплачено. Если не было, то 0 по-умолчанию
        #     if bonds_and_coupons_info[figi]['previous_coupon_date']:
        #         bond_operations = client.operations.get_operations(
        #             account_id=broker_account_info['id'],  # ID счёта (обязательно)
        #             from_=datetime.combine(bonds_and_coupons_info[figi]['previous_coupon_date'],
        #                                    datetime.min.time()),  # с какой даты
        #             to=datetime.combine(bonds_and_coupons_info[figi]['previous_coupon_date'] + timedelta(days=7),
        #                                 datetime.min.time()),  # по какую дату
        #             figi=bonds_and_coupons_info[figi]['bond_figi']  # figi конкретного инструмента
        #         ).operations
        #
        #         for x in bond_operations:
        #             if x.type == 'Выплата купонов' and x.state.OPERATION_STATE_EXECUTED == 1:
        #                 bonds_and_coupons_info[figi]['paid_amount'] = _parse_money_value(x.payment)
        #
        # for_bonds_table = ['figi', 'ticker', 'instrument_id', 'instrument_type', 'bond_name', 'nominal',
        #                    'currency', 'sector', 'maturity_date', 'coupon_quantity_per_year', 'first_purchase_date',
        #                    'is_in_portfolio', 'created_at_utc', 'updated_at_utc']
        #
        # # собираю справочник по облигациям для загрузки в postgres
        # figi_to_name = {pos['figi']: pos['name'] for pos in my_positions}
        # figi_to_uid = {pos['figi']: pos['uid'] for pos in my_positions}
        # bonds_for_db = {}
        # for figi, data in bonds_and_coupons_info.items():
        #     bonds_for_db[figi] = {
        #         'figi': figi,
        #         'ticker': data['ticker'],
        #         'instrument_id': figi_to_uid[figi],
        #         'instrument_type': 'bond',
        #         'bond_name': figi_to_name[figi],
        #         'nominal': data['nominal'],
        #         'currency': data['currency'],
        #         'sector': data['sector'],
        #         'maturity_date': data['maturity_date'],
        #         'coupon_quantity_per_year': data['coupon_quantity_per_year'],
        #         'first_purchase_date': data['first_purchase_date'],
        #         'is_in_portfolio': []
        #     }
        #
        # print(my_positions, bonds_and_coupons_info['BBG01MVSHPP3'], sep='\n\n')






        #==================================
        # план
        # 1. записать в json даты первых покупок облигаций в папку проекта (пока не начну реализовывать в airflow,
        # там уже нужно будет в postgres залить таблицей) - ОК
        # 2. профильтровать выплаты на предмет дат первых покупок, чтобы не получилось так, что думаешь, что выплата
        # предполагалась, а на самом деле нет, т.к. купил первый раз после даты выплаты - ОК
        # 3. проверить и организовать все аккуратно, при необходимости в функции и классы
        # 4. добавить дату выплаты в период от указанной даты + 14 дней - ОК

        #==================================





        # for x in bonds_and_coupons_info:
        #     bond_operations = client.operations.get_operations(
        #         account_id=broker_account_info['id'],  # ID счёта (обязательно)
        #         from_=bonds_and_coupons_info[x]['previous_coupon_date'],  # с какой даты
        #         to=bonds_and_coupons_info[x]['previous_coupon_date'] + timedelta(days=14),  # по какую дату
        #         #     state=...,  # OperationState — статус операции
        #         figi=bonds_and_coupons_info[x]['bond_figi']  # figi конкретного инструмента
        #     ).operations
        #
        #     # print(bonds_and_coupons_info[x])
        #     for x in bond_operations:
        #         # print(x)
        #         # if x.type == 'Выплата купонов' and x.state.OPERATION_STATE_EXECUTED == 1:
        #             # print(x)
        #     break

        # создать справочник, в котором будут первые покупки облигаций с момента начала инвестирования (2025 год)
        # type='Покупка ценных бумаг'
        #

        #=================================
        # добавить дату первой покупки облигации для понимания,
        # должна ли быть выплата купонов

        # добавить дату выплаты в период от указанной даты + 14 дней
        # в get_operations в payment указывается общая сумма выплаты, а не за 1 одну облигацию
        #=================================
                    #     print(pd.DataFrame([bonds_and_coupons_info[x]]))
        #     print(my_positions)
        #     print(bond)
        #     break
        # print(pd.DataFrame(bonds_and_coupons_info))

        # Операции по счету



        # '''
        # Акции
        # Валюта, сектор
        # ================
        # Дивиденды
        # Дата ближайших дивидендов, сумма дивидендов, регулярность выплат, доход
        # Дата предыдущих дивидендов, сумма дивидендов, регулярность выплат, доход
        # '''
        # share_uids = [x['instrument_uid'] for x in my_positions if x['instrument_type'] == 'share']
        # shares_and_dividends_info = {}
        # for s in share_uids:
        #         '''Акции'''
        #         share = client.instruments.share_by(id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID,
        #                                          id=s).instrument
        #         '''Дивиденды. Следующий и предыдущий'''
        #         next_div = None
        #         for ndiv in client.instruments.get_dividends(from_= today, to= today + timedelta(days=90),
        #                                                      instrument_id=s).dividends:
        #             if next_div is None:
        #                 next_div = ndiv
        #             if next_div is not None and ndiv.payment_date < next_div.payment_date:
        #                 next_div = ndiv
        #
        #         prev_div = None
        #         for pdiv in client.instruments.get_dividends(from_= today - timedelta(days=365), to= today,
        #                                                      instrument_id=s).dividends:
        #             if prev_div is None:
        #                 prev_div = pdiv
        #             if prev_div is not None and pdiv.payment_date > prev_div.payment_date:
        #                 prev_div = pdiv
        #
        #         '''Добавляю информацию в словарь об акциях и дивидендах'''
        #         shares_and_dividends_data = {
        #             'currency': share.currency,
        #             'sector': share.sector,
        #             'next_div_payment_date':next_div.payment_date if next_div else None,
        #             'next_div_dividend_net':next_div.dividend_net if next_div else None,
        #             'next_div_regularity':next_div.regularity if next_div else None,
        #             'next_div_yield_value':next_div.yield_value if next_div else None,
        #             'previous_div_payment_date': prev_div.payment_date if prev_div else None,
        #             'previous_div_dividend_net': prev_div.dividend_net if prev_div else None,
        #             'previous_div_regularity': prev_div.regularity if prev_div else None,
        #             'previous_div_yield_value': prev_div.yield_value if prev_div else None
        #         }
        #         shares_and_dividends_info[share.figi] = shares_and_dividends_data
        # print(shares_and_dividends_info)



        # for pos in my_positions:
        #         if pos['instrument_type'] == 'bond':
        #                 pos['coupon_date'] = coupons_info.get(pos['figi'])['coupon_date']
        #                 pos['pay_one_bond'] = coupons_info.get(pos['figi'])['pay_one_bond']
        #                 pos['coupon_type'] = coupons_info.get(pos['figi'])['coupon_type']
        #                 pos['coupon_period'] = coupons_info.get(pos['figi'])['coupon_period']
        #         else:
        #                 pos['coupon_date'] = None
        #                 pos['pay_one_bond'] = None
        #                 pos['coupon_type'] = None
        #                 pos['coupon_period'] = None
        #
        # print(my_positions[0])



        #===================================
        # Заметка
        #===================================
        # добавить номинал купона, чтобы посчитать доход
        # его можно взять из GetInstrumentBy
        # также добавить дату погашения, взять скорее всего также можно из GetInstrumentBy

        # выплаты можно посмотреть в OperationsService -> getOperationsByCursor
        # ===================================



        #





        # print(pos[0])
                # print(x for x in client.instruments.get_bond_coupons(instrument_id=b).events)

        # print(bonds)
        # print(my_positions[0].keys())
        # print(my_positions[0]['instrument_uid'])
        # print(client.instruments.get_bond_coupons(instrument_id=my_positions[0]['instrument_uid']).events)

        #
        #
        #         positions_names.append(
        #                 uid: client.instruments \
        #                 .get_instrument_by(id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID,
        #                                    id=uid).instrument.name
        #
        #         ) = [{
        #         uid: client.instruments\
        #                 .get_instrument_by(id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID,
        #                                    id=uid).instrument.name} for uid in instruments_uids]
        #
        # for uid in instruments_uids:
        #         positions_names.append(
        #                 {'name':client.instruments\
        #                         .get_instrument_by(id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID,
        #                                            id=uid).instrument.name,
        #                  'uid':uid})
        # # print(positions_names)
        #
        # for pos in my_positions:
        #         print(pos)

        # positions_names = [{
        #         'name':client.instruments\
        #                 .get_instrument_by(id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID,
        #                                    id=uid).instrument.name} for uid in instruments_uids,
        #         'uid':uid
        #         uid: client.instruments\
        #                 .get_instrument_by(id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID,
        #                                    id=uid).instrument.name} for uid in instruments_uids]

        # for x in positions_names:
        #         print(x)
        #         for k, v in x.items():
        #                 for d in my_positions:
        #                         if d['uid'] == k:
        #
        #
        # print(positions_names)
                # positions_names.append(client.instruments.get_instrument_by(id_type = 'uid', id = uid).instruments)
                # print(dir(client.instruments.get_instrument_by(id_type = 'uid', id = uid).instrument))
        #         break
        # print(positions_names)
        # print(#.share_by(id=['']))

        # my_positions = [x.__dict__ for x in client.operations.get_portfolio(account_id=broker_account_info['id']).positions]
        # print(my_positions[0].keys())
        # print(my_positions[0])
        # a = client.operations.get_portfolio(account_id=broker_account_info['id']).positions[0].__dict__
        # l = []
        # l.append(a)
        # print(a)
        # print(pd.DataFrame(l))
        # for x in client.operations.get_portfolio(account_id=broker_account_info['id']).positions:
                # print(x.__dict__)
        # print(dir(client.operations.get_portfolio(account_id=broker_account_info['id']).total_amount_portfolio))
        # print(client.operations.get_portfolio(account_id=broker_account_info['id']).total_amount_portfolio)
        # print(dir(client.operations.get_portfolio(account_id=broker_account_info['id']).positions[0]))
        # print(client.operations.get_portfolio(account_id=broker_account_info['id']).positions[0].__dict__)

        # print([x for x in dir(client.instruments) if not x.startswith('_')])
        # print([x for x in dir(client.operations) if not x.startswith('_')])
        # print([x for x in dir(client.users) if not x.startswith('_')])
