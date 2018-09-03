
/*
 * FEATURES
 * - Regex parse adwords_id
 *
 * NOTES
 * - Handsontable doesn't support dropdown Key-Value pair right now. We will
 *   just have to send the string over and replace it in the backend.
 *
 *
 * SENDING DATA
 * - JS_SEND: We can either send the data via javascript and then show the feedbacks to
 *   the user inline,
 * - HTML_SUBMIT: OR we can submit the HTML page.
 *
 * HTML_SUBMIT
 * - Con: If user data contains error, then we need to store it in the HTML and
 *   load it when the table reloads. We have to deal with sessions,
 *   deserializing.
 *
 * JS_SEND
 * - Con: If there is an error, we will have to display it inside the table.
 *   There could be inconsistent states, etc.
 *
 * Overall, it might be eaiser to go to with the JS route because you still
 * have to do all the work for HTML_SUBMIT without sessions and deserializing.
 */

function reset(hot) {
  for (var row=0; row < hot.countRows(); ++row) {
    for (var col=0; col < hot.countCols(); ++col) {
      hot.setCellMeta(row, col, 'className', null);
    }
  }
  hot.render()
}

function translate(resp) {
  ret = `Time: ${Date.now()}\n\n`;

  if (resp.success) {
    ret += 'Success!\n\n';
    ret += 'Account Added: ' + resp.accounts_added + '\n';
  } else {
    ret += 'Not Successful!\n\n'

    for (const [row_num_1, list] of Object.entries(resp.errors)) {
      ret +=`Row ${row_num_1}:\n`;

      // Iterate through the fields
      for (var j=0; j<list.length; ++j) {
        let field = list[j][0];
        let errors = list[j][1];

        // Iterate through the errors
        for (var i=0; i<errors.length; ++i) {
          ret += `  ${field}: ${errors[i]}\n`;
        }
      }

      ret += '\n';
    }
    ret += 'Account Added: 0 (No account added until all errors are resolved)';
  }
  return ret;
}

$.ajax({
  'url': 'setup_data',
  'success': function(everything) {

    let hot = new Handsontable(document.getElementById('hotable'), {
      rowHeaders: true,
      startRows:8,
      startCols: everything.column_names.length,
      colHeaders: everything.column_names,
      columns: everything.column_properties,
      contextMenu: ['remove_row'],
      manualColumnResize: true,
      manualRowResize: true,
      stretchH: 'all',
    });

    let add_rows = $('#add_rows');
    let submit = $('#submit');

    add_rows.click(function() {
      hot.alter('insert_row', hot.countRows(), 5)
    });

    Handsontable.dom.addEvent(document.getElementById('submit'), 'click', function() {
      $.post({
        'url': 'submit',
        'data': {'rows': JSON.stringify(hot.getData()) },

        'error': function(resp) {
          alert('Error');
        },

        'success': function (resp) {
          console.log(resp);
          $('#console').text(translate(resp));

          reset(hot);

          if (resp.success && resp.accounts_added > 0) {
            // Add .success to the all the non empty rows
            for (var row=0; row < hot.countRows(); row++) {
              if (!hot.isEmptyRow(row)) {
                for(var col= 0; col < hot.countCols(); col++){
                  hot.setCellMeta(row, col, 'className', 'success');
                }
              }
            }
            hot.render()

            // Disable both buttons
            add_rows.prop('disabled', true);
            submit.prop('disabled', true);

            // Route to index page
            setTimeout(function() {
              window.alert('Thank you. Redirecting...')
              window.location = '/account/';
            }, 3000);

          } else if (!resp.success) {
            // Add .error to the all the rows with errors
            for (const [row_num_1, errors] of Object.entries(resp.errors)) {
              row_num_0 = row_num_1 - 1;
              for(var i = 0; i < hot.countCols(); i++){
                hot.setCellMeta(row_num_0, i, 'className', 'error');
              }
            }
            hot.render()
          }
        },
      });
    });
  },
});

