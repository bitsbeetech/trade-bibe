import time
from datetime import timedelta
import logging
import arrow
import requests
from pandas.io.json import json_normalize
from pandas import DataFrame
import talib.abstract as ta


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_ticker(pair: str, minimum_date: arrow.Arrow) -> dict:
    """
    Request ticker data from Bittrex for a given currency pair
    """
    url = 'https://bittrex.com/Api/v2.0/pub/market/GetTicks'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36',
    }
    params = {
        'marketName': pair.replace('_', '-'),
        'tickInterval': 'OneMin',
        '_': minimum_date.timestamp * 1000
    }
    data = requests.get(url, params=params, headers=headers).json()
    if not data['success']:
        raise RuntimeError('BITTREX: {}'.format(data['message']))
    return data


def parse_ticker_dataframe(ticker: list, minimum_date: arrow.Arrow) -> DataFrame:
    """
    Analyses the trend for the given pair
    :param pair: pair as str in format BTC_ETH or BTC-ETH
    :return: DataFrame
    """
    df = DataFrame(ticker) \
        .drop('BV', 1) \
        .rename(columns={'C':'close', 'V':'volume', 'O':'open', 'H':'high', 'L':'low', 'T':'date'}) \
        .sort_values('date')
    return df[df['date'].map(arrow.get) > minimum_date]


def populate_indicators(dataframe: DataFrame) -> DataFrame:
    """
    Adds several different TA indicators to the given DataFrame
    """
    dataframe['close_30_ema'] = ta.EMA(dataframe, timeperiod=30)
    dataframe['close_90_ema'] = ta.EMA(dataframe, timeperiod=90)

    dataframe['sar'] = ta.SAR(dataframe, 0.02, 0.2)

    # calculate StochRSI
    stochrsi = ta.STOCHRSI(dataframe)
    dataframe['stochrsi'] = stochrsi['fastd'] # values between 0-100, not 0-1

    macd = ta.MACD(dataframe)
    dataframe['macd'] = macd['macd']
    dataframe['macds'] = macd['macdsignal']
    dataframe['macdh'] = macd['macdhist']

    return dataframe


def populate_buy_trend(dataframe: DataFrame) -> DataFrame:
    """
    Based on TA indicators, populates the buy trend for the given dataframe
    :param dataframe: DataFrame
    :return: DataFrame with buy column
    """
    dataframe.loc[
        (dataframe['stochrsi'] < 20)
        & (dataframe['macd'] > dataframe['macds'])
        & (dataframe['close'] > dataframe['sar']),
        'buy'
    ] = 1
    dataframe.loc[dataframe['buy'] == 1, 'buy_price'] = dataframe['close']
    return dataframe


def analyze_ticker(pair: str) -> DataFrame:
    """
    Get ticker data for given currency pair, push it to a DataFrame and
    add several TA indicators and buy signal to it
    :return DataFrame with ticker data and indicator data
    """
    minimum_date = arrow.utcnow().shift(hours=-6)
    data = get_ticker(pair, minimum_date)
    dataframe = parse_ticker_dataframe(data['result'], minimum_date)
    dataframe = populate_indicators(dataframe)
    dataframe = populate_buy_trend(dataframe)
    return dataframe

def get_buy_signal(pair: str) -> bool:
    """
    Calculates a buy signal based several technical analysis indicators
    :param pair: pair in format BTC_ANT or BTC-ANT
    :return: True if pair is good for buying, False otherwise
    """
    dataframe = analyze_ticker(pair)
    latest = dataframe.iloc[-1]

    # Check if dataframe is out of date
    signal_date = arrow.get(latest['date'])
    if signal_date < arrow.now() - timedelta(minutes=10):
        return False

    signal = latest['buy'] == 1
    logger.debug('buy_trigger: %s (pair=%s, signal=%s)', latest['date'], pair, signal)
    return signal


def plot_dataframe(dataframe: DataFrame, pair: str) -> None:
    """
    Plots the given dataframe
    :param dataframe: DataFrame
    :param pair: pair as str
    :return: None
    """

    import matplotlib

    matplotlib.use("Qt5Agg")
    import matplotlib.pyplot as plt

    # Three subplots sharing x axe
    fig, (ax1, ax2, ax3) = plt.subplots(3, sharex=True)
    fig.suptitle(pair, fontsize=14, fontweight='bold')
    ax1.plot(dataframe.index.values, dataframe['close'], label='close')
    ax1.plot(dataframe.index.values, dataframe['close_30_ema'], label='EMA(30)')
    ax1.plot(dataframe.index.values, dataframe['close_90_ema'], label='EMA(90)')
    # ax1.plot(dataframe.index.values, dataframe['sell'], 'ro', label='sell')
    ax1.plot(dataframe.index.values, dataframe['buy_price'], 'bo', label='buy')
    ax1.legend()

    ax2.plot(dataframe.index.values, dataframe['macd'], label='MACD')
    ax2.plot(dataframe.index.values, dataframe['macds'], label='MACDS')
    ax2.plot(dataframe.index.values, dataframe['macdh'], label='MACD Histogram')
    ax2.plot(dataframe.index.values, [0] * len(dataframe.index.values))
    ax2.legend()

    ax3.plot(dataframe.index.values, dataframe['stochrsi'], label='StochRSI')
    ax3.plot(dataframe.index.values, [80] * len(dataframe.index.values))
    ax3.plot(dataframe.index.values, [20] * len(dataframe.index.values))
    ax3.legend()

    # Fine-tune figure; make subplots close to each other and hide x ticks for
    # all but bottom plot.
    fig.subplots_adjust(hspace=0)
    plt.setp([a.get_xticklabels() for a in fig.axes[:-1]], visible=False)
    plt.show()


if __name__ == '__main__':
    # Install PYQT5==5.9 manually if you want to test this helper function
    while True:
        pair = 'BTC_ANT'
        #for pair in ['BTC_ANT', 'BTC_ETH', 'BTC_GNT', 'BTC_ETC']:
        #   get_buy_signal(pair)
        plot_dataframe(analyze_ticker(pair), pair)
        time.sleep(60)
