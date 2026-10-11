/**
 * Nepal time + Bikram Sambat (वि.सं.) date for Urlabari Interior staff portal.
 * Displays BS as YYYY/MM/DD (e.g. 2083/06/25).
 */
(function (global) {
  // Days in each BS month for years 2000–2090 (index 0 unused). Data from common open converters.
  var BS_MONTHS = {
    2079: [0,31,31,32,31,31,31,30,29,30,29,30,30],
    2080: [0,31,31,32,31,32,30,30,29,30,29,30,30],
    2081: [0,31,32,31,32,31,30,30,30,29,29,30,31],
    2082: [0,31,31,32,31,31,31,30,29,30,29,30,30],
    2083: [0,31,31,32,31,31,31,30,29,30,29,30,30],
    2084: [0,31,32,31,32,31,30,30,30,29,29,30,30],
    2085: [0,31,32,31,32,31,30,30,30,29,30,29,31],
    2086: [0,31,31,32,31,31,31,30,30,29,30,29,30],
    2087: [0,31,31,32,31,31,31,30,30,29,30,29,30],
    2088: [0,31,32,31,32,31,30,30,30,29,29,30,30],
    2089: [0,31,32,31,32,31,30,30,30,29,30,29,31],
    2090: [0,31,31,32,31,31,31,30,30,29,30,29,30]
  };

  // Reference: AD 2024-04-13 = BS 2081-01-01 (Baisakh 1)
  var REF_AD = Date.UTC(2024, 3, 13); // month 0-based: April = 3
  var REF_BS = { y: 2081, m: 1, d: 1 };

  function daysInBsMonth(y, m) {
    var row = BS_MONTHS[y];
    if (row && row[m]) return row[m];
    // fallback approx
    return (m <= 6) ? 31 : 30;
  }

  function daysInBsYear(y) {
    var n = 0;
    for (var m = 1; m <= 12; m++) n += daysInBsMonth(y, m);
    return n;
  }

  /** Convert AD Date (local or any) using calendar parts in Asia/Kathmandu */
  function adPartsInNpt(date) {
    var fmt = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Asia/Kathmandu",
      year: "numeric",
      month: "2-digit",
      day: "2-digit"
    });
    // en-CA → YYYY-MM-DD
    var s = fmt.format(date);
    var p = s.split("-");
    return { y: +p[0], m: +p[1], d: +p[2] };
  }

  function adToBs(date) {
    var ad = adPartsInNpt(date);
    var utc = Date.UTC(ad.y, ad.m - 1, ad.d);
    var diff = Math.round((utc - REF_AD) / 86400000);
    var y = REF_BS.y, m = REF_BS.m, d = REF_BS.d;
    if (diff >= 0) {
      while (diff > 0) {
        var dim = daysInBsMonth(y, m);
        var left = dim - d + 1;
        if (diff >= left) {
          diff -= left;
          d = 1;
          m++;
          if (m > 12) { m = 1; y++; }
        } else {
          d += diff;
          diff = 0;
        }
      }
    } else {
      diff = -diff;
      while (diff > 0) {
        if (d > 1) {
          d--;
          diff--;
        } else {
          m--;
          if (m < 1) { m = 12; y--; }
          d = daysInBsMonth(y, m);
          diff--;
        }
      }
    }
    return { y: y, m: m, d: d };
  }

  function pad(n) { return n < 10 ? "0" + n : "" + n; }

  function formatBs(date) {
    var bs = adToBs(date);
    return bs.y + "/" + pad(bs.m) + "/" + pad(bs.d);
  }

  function formatAdShort(date) {
    return date.toLocaleDateString("en-GB", {
      timeZone: "Asia/Kathmandu",
      day: "2-digit",
      month: "short",
      year: "numeric"
    });
  }

  function formatTime(date) {
    return date.toLocaleTimeString("en-GB", {
      timeZone: "Asia/Kathmandu",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: false
    });
  }

  function tick() {
    var now = new Date();
    var bs = formatBs(now);
    var ad = formatAdShort(now);
    var time = formatTime(now);
    var dateLabel = "वि.सं. " + bs + " · " + ad;
    document.querySelectorAll("#globalNptDate, .js-npt-date").forEach(function (el) {
      el.textContent = dateLabel;
    });
    document.querySelectorAll("#globalNptTime, .js-npt-time").forEach(function (el) {
      el.textContent = time;
    });
  }

  global.UIDNptClock = { tick: tick, adToBs: adToBs, formatBs: formatBs };
  tick();
  setInterval(tick, 1000);
})(window);
