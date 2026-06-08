import os
from datetime import datetime, timezone, timedelta
# some changes

import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', 30)

from dotenv import load_dotenv
from t_tech.invest import Client
from t_tech.invest.schemas import InstrumentIdType

load_dotenv()

TOKEN = os.getenv("T_INVEST_TOKEN")

today = datetime.now(timezone.utc)

# instruments, operations, users

with Client(TOKEN) as client:
        accounts = client.users.get_accounts().accounts
        broker_account_info = [acc for acc in accounts if acc.type == 1][0].__dict__

        '''Все позиции в портфеле'''
        important_columns_positions = ['ticker', 'instrument_uid', 'figi', 'instrument_type', 'quantity', 'quantity_lots',
                             'average_position_price', 'expected_yield', 'current_nkd', 'current_price']
        positions_list = client.operations.get_portfolio(account_id=broker_account_info['id']).positions
        my_positions = [{col: getattr(pos, col, None) for col in important_columns_positions} for pos in positions_list]

        # print(pd.DataFrame(my_positions))

        '''Названия позиций'''
        instruments_uids = [x['instrument_uid'] for x in my_positions]
        positions_names = {}
        for uid in instruments_uids:
                positions_names[uid] = client.instruments\
                                        .get_instrument_by(id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID
                                                           , id=uid).instrument.name
        for pos in my_positions:
                pos['name'] = positions_names.get(pos['instrument_uid'])


        # a = client.instruments.get_bond_coupons(instrument_id='93d49733-cde2-4832-afd7-2274b4dcd96e').events[0] # облигация floating
        # print(a.pay_one_bond, a.coupon_type, a.coupon_date)

        '''
        Инфо по облигациям
        Купонов в год, дата погашения, номинал, сектор, валюта
        ========================================================
        Купоны
        Дата ближайшего купона, тип купона, сумма купона
        Дата предыдущего купона, тип купона, сумма купона
        '''
        # bonds_uids = [x['instrument_uid'] for x in my_positions if x['instrument_type'] == 'bond']
        # bonds_and_coupons_info = {}
        # for b in bonds_uids:
        #         '''Облигации'''
        #         bond = client.instruments.bond_by(id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID,
        #                                          id=b).instrument
        #
        #         '''Купоны. Следующий и предыдущий'''
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
        #         '''Добавляю информацию в словарь об облигациях и купонах'''
        #         bond_and_coupons_data = {
        #             'coupon_quantity_per_year': bond.coupon_quantity_per_year,
        #             'maturity_date': bond.maturity_date,
        #             'nominal': bond.nominal,
        #             'sector': bond.sector,
        #             'currency': bond.currency,
        #             'next_coupon_date': next_coupon.coupon_date if next_coupon else None,
        #             'next_pay_one_bond': next_coupon.pay_one_bond if next_coupon else None,
        #             'next_coupon_type': next_coupon.coupon_type if next_coupon else None,
        #             'previous_coupon_date': previous_coupon.coupon_date if previous_coupon else None,
        #             'previous_pay_one_bond': previous_coupon.pay_one_bond if previous_coupon else None,
        #             'previous_coupon_type': previous_coupon.coupon_type if previous_coupon else None
        #         }
        #         bonds_and_coupons_info[bond.figi] = bond_and_coupons_data

        # print(bonds_and_coupons_info)


        '''
        Акции
        Валюта, сектор
        ================
        Дивиденды
        Дата ближайших дивидендов, сумма дивидендов, регулярность выплат, доход
        Дата предыдущих дивидендов, сумма дивидендов, регулярность выплат, доход
        '''
        share_uids = [x['instrument_uid'] for x in my_positions if x['instrument_type'] == 'share']
        shares_and_dividends_info = {}
        for s in share_uids:
                '''Акции'''
                share = client.instruments.share_by(id_type=InstrumentIdType.INSTRUMENT_ID_TYPE_UID,
                                                 id=s).instrument
                '''Дивиденды. Следующий и предыдущий'''
                next_div = None
                for ndiv in client.instruments.get_dividends(from_= today, to= today + timedelta(days=90),
                                                             instrument_id=s).dividends:
                    if next_div is None:
                        next_div = ndiv
                    if next_div is not None and ndiv.payment_date < next_div.payment_date:
                        next_div = ndiv

                prev_div = None
                for pdiv in client.instruments.get_dividends(from_= today - timedelta(days=365), to= today,
                                                             instrument_id=s).dividends:
                    if prev_div is None:
                        prev_div = pdiv
                    if prev_div is not None and pdiv.payment_date > prev_div.payment_date:
                        prev_div = pdiv

                '''Добавляю информацию в словарь об акциях и дивидендах'''
                shares_and_dividends_data = {
                    'currency': share.currency,
                    'sector': share.sector,
                    'next_div_payment_date':next_div.payment_date if next_div else None,
                    'next_div_dividend_net':next_div.dividend_net if next_div else None,
                    'next_div_regularity':next_div.regularity if next_div else None,
                    'next_div_yield_value':next_div.yield_value if next_div else None,
                    'previous_div_payment_date': prev_div.payment_date if prev_div else None,
                    'previous_div_dividend_net': prev_div.dividend_net if prev_div else None,
                    'previous_div_regularity': prev_div.regularity if prev_div else None,
                    'previous_div_yield_value': prev_div.yield_value if prev_div else None
                }
                shares_and_dividends_info[share.figi] = shares_and_dividends_data
        print(shares_and_dividends_info)
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
