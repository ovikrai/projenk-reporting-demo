"""A standalone, printable HTML executive report with no external assets."""
from html import escape


def currency(value):
    return f"${value:,.2f}"


def insights(metrics):
    top = metrics["categories"][0] if metrics["categories"] else None
    channel = metrics["channels"][0] if metrics["channels"] else None
    growth = metrics["deltas"]["revenue"]
    result = []
    if growth is not None:
        result.append(f"Revenue {'increased' if growth >= 0 else 'decreased'} {abs(growth):.1f}% versus the previous month.")
    else:
        result.append("No previous-month data is available; month-over-month growth is not reported.")
    if top and metrics["revenue"]:
        result.append(f"{top['name']} contributed {top['revenue'] / metrics['revenue'] * 100:.1f}% of net revenue.")
    if channel and metrics["revenue"]:
        result.append(f"{channel['name']} was the leading sales channel at {channel['revenue'] / metrics['revenue'] * 100:.1f}% of revenue.")
    result.append(f"{metrics['refunded_orders']} refunded orders produced a {metrics['refund_rate']:.1f}% refund rate. Review refund drivers before expanding promotions.")
    return result


def render_report(month, metrics, audit):
    table = "".join(f"<tr><td>{escape(item['name'])}</td><td>{item['orders']}</td><td>{currency(item['revenue'])}</td></tr>" for item in metrics["categories"])
    notes = "".join(f"<li>{escape(note)}</li>" for note in insights(metrics))
    cards = "".join(f"<div><small>{label}</small><strong>{value}</strong></div>" for label, value in [
        ("Net revenue", currency(metrics["revenue"])), ("Completed orders", str(metrics["orders"])),
        ("Gross margin", f"{metrics['margin']:.1f}%"), ("Average order value", currency(metrics["aov"]))])
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Projenk · {escape(month)} business report</title>
<style>*{{box-sizing:border-box}}body{{margin:0;background:#fafafa;color:#111111;font:15px/1.7 system-ui,sans-serif}}main{{max-width:860px;margin:40px auto;background:white;padding:52px;border:1px solid #dddddd;border-radius:4px}}header{{display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #eee;padding-bottom:20px}}.brand{{font-size:22px;font-weight:600}}.label{{color:#616161;font-size:11px;letter-spacing:2px;text-transform:uppercase}}h1{{font-size:36px;line-height:1.2;letter-spacing:-1px;margin:30px 0 10px}}h2{{font-size:19px;margin-top:30px}}p{{color:#555555}}.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:20px;background:#f5f5f5;padding:24px;border-radius:2px;margin-top:28px}}small{{display:block;color:#616161}}strong{{display:block;font-size:23px;color:#111111}}table{{width:100%;border-collapse:collapse}}td,th{{padding:12px 8px;border-bottom:1px solid #eee;text-align:left}}td:nth-child(n+2),th:nth-child(n+2){{text-align:right}}footer{{font-size:11px;color:#616161;border-top:1px solid #eee;padding-top:20px;margin-top:32px}}button{{border:0;border-radius:4px;background:#111111;color:white;padding:10px 16px;cursor:pointer}}code{{overflow-wrap:anywhere}}@media(max-width:640px){{main{{margin:0;padding:24px}}.cards{{grid-template-columns:repeat(2,1fr)}}h1{{font-size:28px}}}}@media print{{body{{background:white}}main{{margin:0;border:0;padding:20px}}button{{display:none}}}}</style></head><body><main>
<header><span class="brand">projenk<span style="color:#111111">.</span></span><button onclick="window.print()">Print / save PDF</button></header>
<p class="label">Executive report · synthetic retail business</p><h1>Monthly business review</h1><p>{escape(month)} · USD · Generated from validated synthetic orders</p>
<div class="cards">{cards}</div><h2>What the numbers tell us</h2><ul>{notes}</ul>
<h2>Category performance</h2><table><thead><tr><th>Category</th><th>Orders</th><th>Net revenue</th></tr></thead><tbody>{table}</tbody></table>
<h2>Data quality & methodology</h2><p>The complete input contains {audit['raw_rows']} rows: {audit['accepted_rows']} accepted, {audit['rejected_rows']} rejected and {audit['normalized_rows']} normalized. Metrics above cover only {escape(month)}. Duplicate IDs retain the first valid row; invalid records are excluded and recorded.</p>
<p>Revenue = sum of completed orders × quantity × unit price × (1 − discount / 100), rounded per order to cents. Gross profit = revenue − completed-order cost of goods. Margin = gross profit / revenue. AOV = revenue / completed orders. Refund rate = refunded / (completed + refunded). Refunded and cancelled orders contribute no revenue or cost. Shipping, tax, operating expenses and partial refunds are outside this demo.</p>
<footer>Illustrative data only. No real customers, transactions or business results.<br>Source SHA-256: <code>{audit['source_sha256']}</code></footer></main></body></html>'''
