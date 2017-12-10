# -*- coding: utf-8 -*-
"""
Created on Wed Nov 15 00:24:32 2017

@author: Administrator
"""

# coding:utf-8
import tushare as ts
import talib as ta
import datetime
import sys
sys.path.append('/home/ubuntu/ys')
from MailNotification import MailNotification

# 接收通知邮箱
# RECEIVE_ACCOUNTS = ['deliever_message@sina.com','13922200349@139.com','157504776@qq.com']
RECEIVE_ACCOUNTS = ['181877329@qq.com']
# 回溯长度设置
LOOKBACKDAYS = 4 
# 成交量放大倍数
RATIO = 1.8
# 唐奇安通道设置, 20为短周期，50为长周期
D_Channel = {'up': 20, 'down':10}
# 绘图K线长度
K_Length = 30

def lookback_trade_cal(last, lookbackdays ):
    # 获取交易日历,检查last是否交易日
    trade_cal = ts.trade_cal()
    while not trade_cal[trade_cal.calendarDate == last].isOpen.values:
        last = datetime.datetime.strptime(last, '%Y-%m-%d') - datetime.timedelta(days=1)
        last = last.strftime('%Y-%m-%d')

    trade_cal = trade_cal[trade_cal.isOpen == 1]
    trade_cal.index = range(len(trade_cal))
    first = trade_cal.ix[(trade_cal[trade_cal.calendarDate == last].index[0] - lookbackdays + 1), 0]
    trade_cal.index = range(len(trade_cal))
    first = trade_cal.ix[(trade_cal[trade_cal.calendarDate == last].index[0] - lookbackdays + 1), 0]

    return first, last

def plot_k(data, code, attachs, d_channel = False):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import matplotlib.finance as mpf
    from matplotlib import gridspec
    import os



    fig = plt.figure(figsize = (10,6))
    gs = gridspec.GridSpec(2,1,height_ratios=[2, 0.8])
    ax = plt.subplot(gs[0]) 
    ax2 = plt.subplot(gs[1]) 
    mpf.candlestick2_ochl(ax, data['open'], data['close'], data['high'], data['low'],
                     width=0.6, colorup='red', colordown='green', alpha=1)

    # 绘制唐奇安通道
    if d_channel:
        ax.plot(data['date'], data['d_up'], color='r', label='Donchian Channel Up: {} days'.format(D_Channel['up']))
        ax.plot(data['date'], data['d_down'], color='b',
                label='Donchian Channel Down: {} days'.format(D_Channel['down']))
    ax.legend()
    ax.set_title(code)
    ax.grid(True)

    mpf.volume_overlay(ax2, data['open'], data['close'], data['volume'], colorup='r', colordown='g', width=0.2, alpha=1)
    ax2.set_xticks(range(0, len(data['date']),2))
    ax2.set_xticklabels(data['date'][::2], rotation=45)
    ax2.grid(True)
    plt.subplots_adjust(hspace = 0)
    figPath = os.getcwd()+ '/{}.png'.format(code)
    fig.savefig(figPath,dpi = 100)
    # plt.show()
    attachs.append(figPath)

########### Log记录信息##########
print ("------"*3)
print (datetime.datetime.now().strftime("%Y-%m-%d  %H:%m"))
################################
# 通过 tushare获取股票代码列表
# 中小板 002
#smeList = ts.get_sme_classified()['code']
# 创业板 300
#gemList = ts.get_gem_classified()['code']
# 沪深300
#hs300List = ts.get_hs300s()['code']
# 中证500
#zz500List = ts.get_zz500s()['code']
# A股全部
totList = ts.get_stock_basics().index
# 交易日回溯处理
#last = '2017-11-01'
last = datetime.datetime.today().strftime('%Y-%m-%d')
first,last = lookback_trade_cal(last,LOOKBACKDAYS)

########## Log记录信息##########
print('开始日期: ' + first)
print('结束日期: ' + last)
################################

# 通过tushare获取前lookback_days 个交易日数据,并筛选满足收盘价序列的股票
stockList = totList
#stockList = ['300706']
targetDict = {}
numabc =0
for stock in stockList:
    data = ts.get_k_data(code = stock,start = first, end = last )
    print data
    numabc=numabc+1;
    if numabc==10:
        break
    
    if len(data) == LOOKBACKDAYS:
        c_data = data.close.values
        v_data = data.volume.values
        data_index = 0
        c_flag = True
        v_flag = True

        while data_index < LOOKBACKDAYS - 1:
            if c_data[data_index] < c_data[data_index + 1]:
                data_index += 1
            else:
                c_flag = False
                break
        
	if c_flag:
            data_index = 1
            if v_data[-1* LOOKBACKDAYS ] * RATIO < v_data[data_index]:
                while data_index < LOOKBACKDAYS - 1:
                    if v_data[data_index] > v_data[data_index + 1]:
                        data_index += 1
                    else:
                        v_flag = False
                        break
            else:
                v_flag = False

        if c_flag and v_flag:
            targetDict[stock] = data
    else:
        continue

# 量价条件
cvSet = set()
# 筛选条件1：阳线
positiveSet = set()
# 筛选条件2：MACD > 0, DIFF > DEA
macdSet = set()
# 筛选条件3：ADX >= 30, PDI > MDI
dmiSet = set()
# 筛选条件4：high 突破唐奇安通道
dcSet = set()
# 筛选条件5：一字板股票
# limitupSet = set()


#K线图路径
attachs = []
for code, values in targetDict.items():
    print code
    # 获取条件2,3的OHLC数据
    firstTech, last = lookback_trade_cal(last, 100)
    dataTech = ts.get_k_data(code=code, start=firstTech, end=last)

    # 条件5: 一字板股票
    last5 = dataTech.tail()
    if len(set(last5.mean()[:-2])) == 1:
        targetDict.pop(code)
        # limitupSet.add(code)
        continue

    # 条件1
    if len(values[values.close >= values.open]) == LOOKBACKDAYS:
        positiveSet.add(code)

    # 条件2
    short = 12
    long = 26
    smooth = 9
    diff, dea, hist = ta.MACD(dataTech['close'].values, short, long, smooth)

    if hist[-1] > 0. and diff[-1] > 0. and dea[-1] > 0.:
        macdSet.add(code)

    # 条件3
    adxPeriod = 14
    adx = ta.ADX(dataTech['high'].values, dataTech['low'].values, dataTech['close'].values, adxPeriod)
    pdi = ta.PLUS_DI(dataTech['high'].values, dataTech['low'].values, dataTech['close'].values, adxPeriod)
    mdi = ta.MINUS_DI(dataTech['high'].values, dataTech['low'].values, dataTech['close'].values, adxPeriod)

    if adx[-1] >= 30 and pdi[-1] > mdi[-1]:
        dmiSet.add(code)

    # 计算唐奇安通道
    dataTech['d_up'] = ta.MAX(dataTech['high'].values, D_Channel['up'])
    dataTech['d_up'] = dataTech['d_up'].shift(1)
    dataTech['d_down'] = ta.MIN(dataTech['low'].values, D_Channel['down'])
    dataTech['d_down'] = dataTech['d_down'].shift(1)

    # 条件4
    if targetDict[code].tail(1)['high'].values >= dataTech.tail(1)['d_up'].values:
        dcSet.add(code)

    targetDict[code] = dataTech.tail(1)['d_up'].values[0]
    # print targetDict


    k_data = dataTech.tail(K_Length)
    # print k_data
    plot_k(k_data, code,attachs, True)

# print attachs
    # ax = dataTech['close'].plot()
    # fig = ax.get_figure()
    # fig.savefig('{}.png'.format(code))

# cvSet = set(targetDict.keys) - limitupSet

########## Log记录信息##########
print "满足量价规则： %d" %len(targetDict.keys())
print targetDict
print "满足阳线条件:  %d" %len(positiveSet)
print positiveSet
print "满足MACD条件:  %d" %len(macdSet)
print macdSet
print "满足DMI条件:  %d" %len(dmiSet)
print dmiSet
print "突破唐奇安通道：%d" %len(dcSet)
print dcSet
print "综上，符合所有： %d" %len(list(positiveSet & macdSet & dmiSet & dcSet))
print positiveSet & macdSet & dmiSet & dcSet
################################

# 生成邮件正文
if len(targetDict):
    msgText = '今日共发现{}个股票{}满足量价条件，技术指标筛选如下：\n'.format(len(targetDict), targetDict.keys()) + \
          '[1]满足阳线规则: {} \n'.format(list(positiveSet)) + \
          '[2]满足MACD规则: {} \n'.format(list(macdSet)) + \
          '[3]满足DMI规则: {} \n'.format(list(dmiSet)) + \
          '[4]突破唐奇安通道: {} \n'.format(list(dcSet)) + \
          '符合所有规则有{}个 \n'.format(len(list(positiveSet & macdSet & dmiSet & dcSet)))

    msgHtml = '<html><body><div><div>今日共发现<b><font color="#ff0000">{}</font></b>个股票<b><font color="#ff0000">{}</font></b>满足量价条件，技术指标筛选如下：</div>'.format(
        len(targetDict),targetDict.keys()) \
              + '<div><b>[1]满足阳线规则:</b> {}&nbsp;</div>'.format(list(positiveSet)) \
              + '<div><b>[2]满足MACD规则:</b> {}&nbsp;</div>'.format(list(macdSet)) \
              + '<div><b>[3]满足DMI规则:</b> {}&nbsp;</div>'.format(list(dmiSet)) \
              + '<div><b>[4]突破唐奇安通道:</b> {}&nbsp;</div>'.format(list(dcSet)) \
              + '<div>符合所有规则有{}个, 近{}个交易日走势如下&nbsp;</div></div>'.format(len(list(positiveSet & macdSet & dmiSet)),K_Length) \

    for i in targetDict.keys():
        msgHtml = msgHtml + \
                '<div><b>【{}】</b>&nbsp;：建议入场价{}元</div>'.format(i, targetDict[i]) +\
                '<img src="cid:{}" alt="{}">'.format(i, i, i)
    msgHtml = msgHtml + '</body></html>'

else:
    msgText = '今日无收获.....'
    msgHtml = '<html><body><b>今日无收获.....</b></body></html>'


subject = last + ': '
# 发送通知
with MailNotification(RECEIVE_ACCOUNTS) as mail:
   if len(targetDict):
       subject = subject + u'恭喜发财! 发现{}个目标股'.format(len(targetDict))
   else:
       subject = subject + u'稍安勿躁! 未发现目标股'

   mail.send_multi(subject, msgHtml, 'html', attachs)
   # mail.send_notification(subject, msgText, 'plain', attachs)
