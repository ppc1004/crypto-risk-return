// Shared helpers for all pages. Numbers come from data/metrics.json,
// which is created by src/analysis.py.

var COIN_ORDER = ["BTC", "ETH", "USDT", "BNB", "XRP"];

function loadData() {
  return fetch("data/metrics.json").then(function (r) { return r.json(); });
}

function pct(x, digits) {
  if (digits === undefined) digits = 0;
  var v = (x * 100).toFixed(digits);
  if (parseFloat(v) === 0) return (0).toFixed(digits) + "%";
  return x > 0 ? "+" + v + "%" : v + "%";
}
function pctPlain(x, digits) {
  if (digits === undefined) digits = 0;
  var v = (x * 100).toFixed(digits);
  if (parseFloat(v) === 0) v = (0).toFixed(digits);
  return v + "%";
}
function num(x, digits) { return x.toFixed(digits === undefined ? 2 : digits); }
function money(x) {
  if (x >= 100) return "$" + Math.round(x).toLocaleString("en-US");
  if (x >= 1) return "$" + x.toFixed(2);
  return "$" + x.toFixed(4);
}
function niceDate(s) {
  var d = new Date(s + "T00:00:00");
  return d.toLocaleDateString("en-US", { month: "short", year: "numeric" });
}
function dot(color) { return '<span class="dot" style="background:' + color + '"></span>'; }

// Fill any element like <span data-v="five_year.BTC.total_return|pct">
function fillValues(data) {
  document.querySelectorAll("[data-v]").forEach(function (el) {
    var parts = el.getAttribute("data-v").split("|");
    var value = parts[0].split(".").reduce(function (o, k) { return o[k]; }, data);
    var fmt = parts[1] || "pct";
    if (fmt === "pct") el.textContent = pct(value);
    else if (fmt === "pctPlain") el.textContent = pctPlain(value);
    else if (fmt === "abs") el.textContent = pctPlain(Math.abs(value));
    else if (fmt === "pct1") el.textContent = pctPlain(value, 1);
    else if (fmt === "num") el.textContent = num(value);
    else if (fmt === "date") el.textContent = niceDate(value);
    else el.textContent = value;
  });
}

function metricsTable(rows, colors) {
  var cols = [
    ["total_return", "Total return", pct],
    ["annual_return", "Per year", pct],
    ["annual_volatility", "Risk (volatility)", function (x) { return pctPlain(x); }],
    ["max_drawdown", "Worst fall from peak", function (x) { return pctPlain(x); }],
    ["sharpe_ratio", "Sharpe ratio", function (x) { return num(x); }]
  ];
  var html = '<table><thead><tr><th>Coin</th>';
  cols.forEach(function (c) { html += "<th>" + c[1] + "</th>"; });
  html += "</tr></thead><tbody>";
  COIN_ORDER.forEach(function (coin) {
    var r = rows[coin];
    html += '<tr><td>' + dot(colors[coin]) + '<a href="coin.html?c=' + coin + '">' + r.name + "</a></td>";
    cols.forEach(function (c) {
      var v = r[c[0]];
      var cls = (c[0] === "total_return" || c[0] === "annual_return") ? (v <= -0.005 ? "neg" : (v >= 0.005 ? "pos" : "")) : "";
      html += '<td class="' + cls + '">' + c[2](v) + "</td>";
    });
    html += "</tr>";
  });
  return html + "</tbody></table>";
}
