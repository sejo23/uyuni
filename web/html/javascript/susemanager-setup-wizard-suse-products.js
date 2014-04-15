$(function(){
  showProducts();

  // click on an add product icon. Handler is attached to table because rows
  // can be reloaded via AJAX
  $("#table-content").on("click", ".start-sync-icon", function(event) {
    var ident = $(this).closest("tr").data("ident");

    showSyncStarting(ident);

    ProductSyncAction.synchronizeSingle(ident, makeAjaxHandler(function() {
      showSyncStarted(ident);
    }));
  });

  // handles select all top/bottom checkboxes
  $("input.select-all").change(function() {
    $("#suse-products input[type='checkbox']:enabled").prop("checked", $(this).is(":checked"));
  });

  // handles synchronize bottom button
  $("#synchronize").click(function() {
    var checkboxes = $("#table-content input[type='checkbox']:checked:enabled");
    var idents = checkboxes.closest("tr").map(function() {
      return $(this).data("ident");
    }).toArray();

    $.each(idents, function(){
      showSyncStarting(this);
    });

    ProductSyncAction.synchronizeMultiple(idents, makeAjaxHandler(function() {
      $.each(idents, function(){
        showSyncStarted(this);
      });
    }));
  });

  // handles clicks on product checkboxes
  $("#table-content").on("change", "input", function(event) {
    var checked = $(this).prop("checked");
    var row = $(this).closest("tr");
    var baseProductIdent = row.data("baseproductident");
    var base = baseProductIdent == "";

    if (!checked && base) {
      var productIdent = row.data("ident");
      $("tr[data-baseproductident='" + productIdent + "']")
        .find("input")
        .prop("checked", false);
    }
    if (checked && !base) {
      $("tr[data-ident='" + baseProductIdent + "']")
        .find("input")
        .prop("checked", true);
    }
  });

  // Get the products and show message in case of errors
  function showProducts() {
    ProductsRenderer.renderAsync(makeAjaxHandler(
      function(content) {
        $("#loading-placeholder").hide();
        $("#table-content").append(content);
      },
      function(message, exception) {
        if (exception.javaClassName.indexOf("InvalidMirrorCredentialException") > 0) {
          $('.table').hide();
          $("#alert-popup").show();
        }
        else {
          showFatalError();
        }
      })
    );
  }

  function getRow(ident) {
    return $("#table-content tr[data-ident='" + ident + "']");
  }

  function showSyncStarting(ident) {
    var row = getRow(ident);
    row.find(".start-sync-icon").hide();
    row.find(".starting-sync-icon").show();
  }

  function showSyncStarted(ident) {
    var row = getRow(ident);
    row.find(".starting-sync-icon").hide();
    row.find(".sync-started-icon").show();

    var checkbox = row.find("input[type='checkbox']");
    checkbox.prop("checked", true);
    checkbox.prop("disabled", true);

    var addonRows = $("tr[data-baseproductident='" + ident + "']");
    var addonStartSyncIcons =  addonRows.find(".start-sync-icon");
    var addonCheckboxes = addonRows.find("input[type='checkbox']");

    addonStartSyncIcons.show();
    addonCheckboxes.removeAttr("disabled");
  }
});
