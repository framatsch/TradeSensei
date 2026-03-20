import xml.etree.ElementTree as ET
import os
import random


def anonymize_xml(input_path, output_path, limit=50):
    tree = ET.parse(input_path)
    root = tree.getroot()

    # Random offset for prices and quantities to disguise exact portfolio value
    price_multiplier = random.uniform(0.9, 1.1)

    # Consistent mapping for account
    new_account_id = "DU1234567"

    # 1. Update FlexStatement attributes
    for statement in root.findall(".//FlexStatement"):
        statement.set("accountId", new_account_id)

    # 2. Process CashReport
    for report in root.findall(".//CashReportCurrency"):
        report.set("accountId", new_account_id)
        for attr, val_str in report.attrib.items():
            if any(
                key in attr.lower()
                for key in [
                    "cash",
                    "amount",
                    "fees",
                    "commissions",
                    "dividends",
                    "interest",
                    "sales",
                    "purchases",
                ]
            ):
                try:
                    val = float(val_str)
                    report.set(attr, f"{val * price_multiplier:.4f}")
                except (ValueError, TypeError):
                    pass

    # 3. Process Trades (Limit count)
    trades_container = root.find(".//Trades")
    if trades_container is not None:
        all_trades = trades_container.findall("Trade")
        for trade in all_trades[limit:]:
            trades_container.remove(trade)

        for trade in trades_container.findall("Trade"):
            trade.set("accountId", new_account_id)
            trade.set("tradeID", str(random.randint(10000000, 99999999)))
            trade.set("transactionID", str(random.randint(1000000000, 9999999999)))
            trade.set("ibOrderID", str(random.randint(100000000, 999999999)))

            if "orderReference" in trade.attrib:
                trade.set("orderReference", "REF-" + str(random.randint(1000, 9999)))
            if "ibExecID" in trade.attrib:
                trade.set("ibExecID", "EXEC-" + str(random.randint(1000, 9999)))

            for attr in ["tradePrice", "tradeMoney"]:
                val_str = trade.get(attr)
                if val_str:
                    try:
                        val = float(val_str)
                        trade.set(attr, f"{val * price_multiplier:.4f}")
                    except (ValueError, TypeError):
                        pass

    # 4. Process OpenPositions (Limit count)
    positions_container = root.find(".//OpenPositions")
    if positions_container is not None:
        all_pos = positions_container.findall("OpenPosition")
        for pos in all_pos[limit:]:
            positions_container.remove(pos)

        for pos in positions_container.findall("OpenPosition"):
            pos.set("accountId", new_account_id)
            val_str = pos.get("positionValue")
            if val_str:
                try:
                    val = float(val_str)
                    pos.set("positionValue", f"{val * price_multiplier:.2f}")
                except (ValueError, TypeError):
                    pass

    tree.write(output_path, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    src_dir = "/home/scheffold/work/tradejournal/tmp"
    dest_dir = "/home/scheffold/work/tradejournal/tests/test_data/ibkr"
    files = [
        "TraderJournal_2023.xml",
        "TraderJournal_2024.xml",
        "TraderJournal_2025.xml",
    ]

    for f in files:
        in_p = os.path.join(src_dir, f)
        out_p = os.path.join(dest_dir, f.replace(".xml", "_anonymized.xml"))
        if os.path.exists(in_p):
            print(f"Anonymizing {f}...")
            anonymize_xml(in_p, out_p, limit=30)
        else:
            print(f"File {f} not found.")
