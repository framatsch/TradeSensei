import argparse
import csv
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

def _init_year_bucket():
    return {"total": 0.0, "winners": 0.0, "losers": 0.0, "commission": 0.0}



def parse_flex_query(file_paths):
    results = defaultdict(_init_year_bucket)

    for file_path in file_paths:

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            for trade in root.findall('.//Trade'):
                trade_date = trade.get('tradeDate')
                if not trade_date:
                    continue

                year = trade_date[:4]
                try:
                    pnl = float(trade.get('fifoPnlRealized', '0'))
                    ibCommission = float(trade.get('ibCommission', '0'))
                    commission = float(trade.get('commission', '0'))
                #    fx_rate = float(trade.get('fxRateToBase', '1'))
                except ValueError:
                    continue

                print(f"Processing trade on {trade_date}: P&L={pnl}, IB Commission={ibCommission}, Commission={commission}", file=sys.stderr    )
                results[year]["total"] += pnl
                results[year]['commission'] += max(abs(ibCommission), abs(commission))
                results[year]["trades"]= results[year].get("trades", 0) + 1
                if pnl > 0:
                    results[year]["winners"] += pnl
                else:
                    results[year]["losers"] += pnl

        except Exception as e:
            print(f"Error reading file {file_path}: {e}", file=sys.stderr)

    return results

def main():
    parser = argparse.ArgumentParser(description="Aggregate trades from IBKR FlexQuery XML files.")
    parser.add_argument('files', metavar='FILE', type=str, nargs='+', help='Paths to the XML files')
    parser.add_argument('--yaml-output', action='store_true', help='Output the results in YAML format')
    args = parser.parse_args()

    results = parse_flex_query(args.files)

    output_data = {}
    for year in sorted(results.keys()):
        data = results[year]

        output_data[year] = {

            'winners': round(data['winners'], 2),
            'losers': round(data['losers'], 2),
            'total': round(data['total'], 2),
            'commission': round(data['commission'], 2),

        }

    if args.yaml_output:
        print(yaml.dump(output_data, default_flow_style=False, sort_keys=True))
    else:
        console = Console()
        table = Table(title="IBKR Trade P&L Aggregation", show_lines=True)

        table.add_column("Year", justify="left", style="cyan", no_wrap=True)
        table.add_column("Gross Winners", justify="right", style="green")
        table.add_column("Gross Losers", justify="right", style="red")
        table.add_column("Gross Total", justify="right")
        table.add_column("Commission Fees", justify="right")
        table.add_column("Net Total", justify="right")
        table.add_column("Trades", justify="right")


        for year in sorted(output_data.keys()):
            d = output_data[year]
            table.add_row(
                year,
                f"{d['winners']:.2f}",
                f"{d['losers']:.2f}",
                f"{d['total']:.2f}",
                f"{d['commission']:.2f}",
                f"{d['total'] + d['commission']:.2f}",
                str(results[year].get("trades", 0))
            )
        console.print(table)

if __name__ == '__main__':
    main()