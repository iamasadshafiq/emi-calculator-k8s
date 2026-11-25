// Loan EMI Calculator - the form is sent with AJAX, the page is never reloaded.

function money(x) {
  return Number(x).toLocaleString("en-US", {minimumFractionDigits: 2, maximumFractionDigits: 2});
}

// client-side validation: positive numbers only, months must be a whole number
function validate() {
  var ok = true;
  var p = parseFloat($("#principal").val());
  var r = parseFloat($("#rate").val());
  var n = Number($("#months").val());

  $("#principal").toggleClass("is-invalid", !(p > 0));
  $("#rate").toggleClass("is-invalid", !(r > 0));
  $("#months").toggleClass("is-invalid", !(n > 0 && Number.isInteger(n)));

  if ($("#emi-form .is-invalid").length > 0) { ok = false; }
  return ok ? {principal: p, rate: r, months: n} : null;
}

function loadHistory() {
  $.getJSON("/api/history")
    .done(function (rows) {
      var body = $("#history-body").empty();
      if (rows.length === 0) {
        body.append('<tr><td colspan="7" class="text-muted">No calculations yet.</td></tr>');
        return;
      }
      $.each(rows, function (i, row) {
        var tr = $("<tr>");
        tr.append($("<td>").text(i + 1));
        tr.append($("<td>").text(money(row.principal)));
        tr.append($("<td>").text(row.rate));
        tr.append($("<td>").text(row.months));
        tr.append($("<td>").text(money(row.emi)));
        tr.append($("<td>").text(row.servedBy));
        tr.append($("<td>").text(new Date(row.createdAt).toLocaleString()));
        body.append(tr);
      });
    })
    .fail(function () {
      $("#history-body").html('<tr><td colspan="7" class="text-danger">Could not load the history.</td></tr>');
    });
}

$(function () {
  loadHistory();

  $("#emi-form").on("submit", function (e) {
    e.preventDefault();                       // no postback
    $("#error-box").addClass("d-none");
    var data = validate();
    if (!data) { return; }

    $("#btn-calc").prop("disabled", true);
    $.ajax({
      url: "/api/emi",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify(data)
    })
      .done(function (res) {
        $("#res-emi").text(money(res.emi));
        $("#res-total").text(money(res.totalPayment));
        $("#res-interest").text(money(res.totalInterest));
        $("#res-pod").text(res.servedBy);
        $("#res-ip").text(res.podIP);
        $("#result-empty").addClass("d-none");
        $("#result-body").removeClass("d-none");
        loadHistory();                        // only the result panel and the table change
      })
      .fail(function (xhr) {
        var msg = "Request failed (HTTP " + xhr.status + ").";
        if (xhr.responseJSON && xhr.responseJSON.details) {
          msg = $.map(xhr.responseJSON.details, function (v, k) { return k + " " + v; }).join(", ");
        } else if (xhr.responseJSON && xhr.responseJSON.error) {
          msg = xhr.responseJSON.error;
        }
        $("#error-box").text(msg).removeClass("d-none");
      })
      .always(function () {
        $("#btn-calc").prop("disabled", false);
      });
  });
});
