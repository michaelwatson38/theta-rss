#!/usr/bin/env python
"""Generate RSS feeds from trades on thetagang.com."""
import json

from dateutil import parser
from feedgen.feed import FeedGenerator
import peewee
import requests


db = peewee.SqliteDatabase('feeds.db')

class Trade(peewee.Model):

    # Basics
    guid = peewee.UUIDField(primary_key=True)

    # Trade parameters
    long_put = peewee.FloatField(null=True)
    long_call = peewee.FloatField(null=True)
    short_put = peewee.FloatField(null=True)
    short_call = peewee.FloatField(null=True)
    price_filled = peewee.FloatField(null=True)
    price_closed = peewee.FloatField(null=True)

    # Other trade data
    payment = peewee.CharField()
    quantity = peewee.IntegerField()
    symbol = peewee.CharField()
    trade_type = peewee.CharField()

    # Booleans and flags
    assigned = peewee.BooleanField(null=True)
    earnings = peewee.BooleanField()
    win = peewee.BooleanField(null=True)

    # Dates
    expiry_date = peewee.DateTimeField(null=True)
    close_date = peewee.DateTimeField(null=True)
    open_date = peewee.DateTimeField()
    updated_at = peewee.DateTimeField()

    # Notes
    opening_note = peewee.TextField(null=True)
    closing_note = peewee.TextField(null=True)

    # User data.
    user_name = peewee.CharField()
    user_role = peewee.CharField()

    class Meta:
        database = db

Trade.create_table()


def get_trades():
    """Retrieve the latest set of trades."""
    resp = requests.get("https://api.thetagang.com/trades")
    return resp.json()['data']['trades']
    # with open('trades', 'rb') as fileh:
    #     return json.load(fileh)['data']['trades']


def generate_feed(trades_for_feed, description, filename):
    fg = FeedGenerator()
    fg.title(f"ThetaGang Trades: {description}")
    fg.link(href="https://thetagang.com/")
    fg.description(f"ThetaGang Trades: {description}")

    for index, trade in enumerate(trades_for_feed):
        short_summary, long_summary = get_trade_summary(trade)

        item = fg.add_entry()
        if trade.close_date:
            item.id(f"{str(trade.guid)}-closing")
        else:
            item.id(f"{str(trade.guid)}-opening")
        item.link(href=f"https://thetagang.com/{trade.user_name}/{trade.guid}")
        item.title(short_summary)
        item.description(long_summary)
        item.pubDate(trade.updated_at)

    fg.rss_file(filename, pretty=True)


def get_emoji(trade):
    if trade.close_date:
        return "🏁"
    else:
        return "🌅"


def get_trade_summary(trade):
        # Are we opening or closing?
        winner = None
        if trade.close_date:
            action = "closed a"
            winner = False
            if trade.win:
                winner = True
        else:
            action = "opened a"

        expiration_string = ""
        if trade.expiry_date:
            expiration_date = parser.parse(trade.expiry_date).strftime("%Y-%m-%d")
            expiration_string = f"expiring {expiration_date}"
        short_summary = (
            f"{get_emoji(trade)} {trade.user_name} {action} "
            f"{trade.trade_type.lower()} on ${trade.symbol} {expiration_string}"
        )

        long_summary = (
            "For more details, "
            f"<a href='https://thetagang.com/{trade.user_name}/{trade.guid}'>"
            "view this trade on thetagang.com</a>"
        )
        return (short_summary, long_summary)

for new_trade in get_trades():
    user_id = (
        Trade.replace(
            # Basics
            guid=new_trade["guid"],

            # Trade parameters
            long_put=new_trade["long_put"],
            long_call=new_trade["long_call"],
            short_put=new_trade["short_put"],
            short_call=new_trade["short_call"],
            price_filled=new_trade["price_filled"],
            price_closed=new_trade["price_closed"],

            # Other trade data
            payment=new_trade["payment"],
            quantity=new_trade["quantity"],
            symbol=new_trade["symbol"],
            trade_type=new_trade["type"],

            # Booleans and flags
            assigned=new_trade["assigned"],
            earnings=new_trade["earnings"],
            win=new_trade["win"],

            # Dates
            expiry_date=new_trade["expiry_date"],
            close_date=new_trade["close_date"],
            open_date=new_trade["open_date"],
            updated_at=new_trade["updatedAt"],

            # Notes
            opening_note=new_trade["note"],
            closing_note=new_trade["closing_note"],

            # User data.
            user_name=new_trade["User"]["username"],
            user_role=new_trade["User"]["role"],
        ).execute()
    )

print(
    Trade.select().count()
)


# Generate a feed for all trades.
all_trades = (
    Trade
    .select()
    .order_by(Trade.updated_at.desc())
    .limit(100)
)
generate_feed(all_trades, "All trades", "trades_all.xml")

# Get trades from patrons only.
all_trades = (
    Trade
    .select()
    .where(Trade.user_role=='patron')
    .order_by(Trade.updated_at.desc())
    .limit(100)
)
generate_feed(all_trades, "Patreon trades only", "trades_patron.xml")

# Get winning trades only.
all_trades = (
    Trade
    .select()
    .where(Trade.win==True)
    .order_by(Trade.updated_at.desc())
    .limit(100)
)
generate_feed(all_trades, "Winning trades only", "trades_winning.xml")

# Get losing trades only.
all_trades = (
    Trade
    .select()
    .where(Trade.win==False)
    .order_by(Trade.updated_at.desc())
    .limit(100)
)
generate_feed(all_trades, "Losing trades only", "trades_losing.xml")

# Get a specific trade type.
trade_types = (
    Trade
    .select(Trade.trade_type)
    .order_by(Trade.trade_type)
    .distinct()
)

for trade_type in [x.trade_type for x in trade_types]:
    trade_type_filename = trade_type.lower().replace(" ", "_")
    trades_for_type = (
        Trade
        .select()
        .where(Trade.trade_type==trade_type)
        .order_by(Trade.updated_at.desc())
        .limit(100)
    )
    generate_feed(
        trades_for_type,
        f"Only {trade_type.lower()} trades",
        f"trades_{trade_type_filename}.xml"
    )
