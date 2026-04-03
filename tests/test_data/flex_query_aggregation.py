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
    return {"pnl": 0.0,
            "commission": 0.0,
            }



def parse_flex_query(file_paths):
    results = defaultdict(_init_year_bucket)
    # Ensure 'total' bucket exists
    results["total"]

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

                #print(f"Processing trade on {trade_date}: fifoPnlRealized={pnl}, IB Commission={ibCommission}, Commission={commission}", file=sys.stderr    )
                comm= max(abs(ibCommission), abs(commission))
                results["total"]["pnl"] += pnl
                results["total"]["commission"] += comm
                results[year]["pnl"] += pnl
                results[year]['commission'] += comm

            results["total"]["gross_pnl"] = results["total"]["pnl"] + results["total"]["commission"]

        except Exception as e:
            print(f"Error reading file {file_path}: {e}", file=sys.stderr)

    return results

def main():
    parser = argparse.ArgumentParser(description="Aggregate trades from IBKR FlexQuery XML files.")
    parser.add_argument('files', metavar='FILE', type=str, nargs='+', help='Paths to the XML files')
    parser.add_argument('--yaml-output', action='store_true', help='Output the results in YAML format')
    args = parser.parse_args()

    results = parse_flex_query(args.files)

    # YAML output
    if args.yaml_output:
        # Runde alle Werte für die Ausgabe
        yaml_out = {}
        for year in sorted(results.keys()):
            data = results[year]
            yaml_out[year] = {
                'pnl': round(data['pnl'], 2),
                'commission': round(data['commission'], 2),
            }
            if year == 'total' and 'gross_pnl' in data:
                yaml_out[year]['gross_pnl'] = round(data['gross_pnl'], 2)
        print(yaml.dump(yaml_out, default_flow_style=False, sort_keys=True))
        return

    # Console output
    console = Console()
    # Yearly table
    table = Table(title="IBKR Yearly Trade P&L Aggregation", show_lines=True)
    table.add_column("Year", justify="left", style="cyan", no_wrap=True)
    table.add_column("Commission", justify="right")
    table.add_column("Net PnL", justify="right")
    for year in sorted(k for k in results.keys() if k != 'total'):
        data = results[year]
        table.add_row(
            year,
            f"{data['commission']:.2f}",
            f"{data['pnl']:.2f}"
        )
    console.print(table)

    # Total table
    if 'total' in results:
        total = results['total']
        table = Table(title="IBKR Total Aggregation", show_lines=True)
        table.add_column("Total", justify="left", style="cyan", no_wrap=True)
        table.add_column("Commission", justify="right")
        table.add_column("Net PnL", justify="right")
        if 'gross_pnl' in total:
            table.add_column("Gross PnL", justify="right")
            table.add_row(
                "Total",
                f"{total['commission']:.2f}",
                f"{total['pnl']:.2f}",
                f"{total['gross_pnl']:.2f}"
            )
        else:
            table.add_row(
                "Total",
                f"{total['commission']:.2f}",
                f"{total['pnl']:.2f}"
            )
        console.print(table)

if __name__ == '__main__':
    main()