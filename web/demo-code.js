function confirm_delete_schedule() {
	bootbox.confirm("Are you sure you want to delete this schedule?", function(result) {
		console.log("Delete confirmation result: " + result);
	});
}

function choose_file(filename) {
	$("#selected-filename").html(filename);
}

$(document).ready(function() {
	var prog = $("#progress");
	var pos = 31;
	setInterval(function() {
		pos += 1;
		if (pos > 1415) pos = 1415;
		var seconds = pos % 60;
		var minutes = Math.floor(pos / 60);
		var sec_string = ((seconds < 10) ? "0" : "") + seconds;
		var min_string = ((minutes < 10) ? "0" : "") + minutes;
		prog.html(min_string + ":" + sec_string);
	}, 1000);
	
	
	$("#testmodal").on('hidden.bs.modal', function() {
		$("#selected-filename").html('Select file for playback');
	});
	
	$('#new-schedule-date').datepicker({
		format: 'dd/mm/yyyy',
		autoclose: true
	});
	
	$('#new-schedule-time').timepicker({
		template: false,
		showInputs: false,
		minuteStep: 5
	});
});

