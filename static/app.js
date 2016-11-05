var files_cache = null;



function chooseFile(el, filename) {
	$(el).parent().parent().parent().find(".selected-filename").html(filename);
}

$(document).ready(function() {
	$("#testmodal").on('hidden.bs.modal', function(e) {
        if (e.target.id != "testmodal") return;
		$("#selected-filename").html('Select file for playback');
        files_cache = null;
	});

    $("#testmodal").on('show.bs.modal', function(e) {
        if (e.target.id != "testmodal") return;
        $(".playlist-item").remove();
        $(".playlist-spacer").remove();
        updateFilesCache();
    });

    $(document).on("click", ".playlist-remove", null, function(event) {
        removeItemFromPlaylist(event);
    });

	$('#new-schedule-date').datepicker({
		format: 'dd/mm/yyyy',
		autoclose: true
	}).datepicker('setDate', new Date());

	$('#new-schedule-time').timepicker({
		template: false,
		showInputs: false,
		minuteStep: 5
	});

    do_radio_status_update();
    refreshSchedules();
});


// Radio state updates

// The regularly-run function to do updates
function do_radio_status_update() {
    $.ajax("/radio/status").done(function(data, status, jqXHR) {
        var s = JSON.parse(data)
        updateInternetFunctionState("echolink", s.echolink_active);
        updateInternetFunctionState("irlp", s.irlp_active);
        updatePTTState(s.ptt);
        updatePlaybackState(s.playback_status);
        updatePlayingFile(s.file_playing);
        updatePlaybackProgress(s.progress);

        setTimeout(function() {
            do_radio_status_update();
        }, 1000);
    });
}


// Functions to update state of page

function updateInternetFunctionState(name, state) {
    var stateDiv = $("#" + name + "-state");
    var enableButton = $("#" + name + "-enable");
    var disableButton = $("#" + name + "-disable");

    if (state) {
        stateDiv.removeClass("disabled").addClass("enabled");
        stateDiv.text("ENABLED");
    } else {
        stateDiv.addClass("disabled").removeClass("enabled");
        stateDiv.text("DISABLED");
    }

    if (state) {
        enableButton.hide();
        disableButton.show();
    } else {
        disableButton.hide();
        enableButton.show();
    }
}

function updatePTTState(state) {
    var el = $("#ptt-state");
    var stopTx = $("#stop-tx");

    if (state) {
        el.removeClass("disabled").addClass("on-air").text("ON AIR");
        stopTx.css('visibility', 'visible');
    } else {
        el.removeClass("on-air").addClass("disabled").text("CLEAR");
        stopTx.css('visibility', 'hidden');
    }
}

function updatePlaybackState(state) {
    var el = $("#player-state");
    if (state == "stopped") el.text("Stopped");
    if (state == "waiting_to_clear") el.text("Waiting for channel to clear");
    if (state == "playing") el.text("Playing");
}

function updatePlayingFile(filename) {
    var el = $("#player-filename");
    el.text(filename);
}

function updatePlaybackProgress(progress) {
    var el = $("#player-progress");
    el.text(progress);
}


// Functions run when you press buttons

// In general we just fire a command at the server and wait for something to happen in our one-second updates

function stopTxNowClicked() {
    $.post("/radio/stop");
}

function enableIRLPClicked() {
    $.post("/radio/enable_irlp");
}

function disableIRLPClicked() {
    $.post("/radio/disable_irlp");
}

function enableEcholinkClicked() {
    $.post("/radio/enable_echolink");
}

function disableEcholinkClicked() {
    $.post("/radio/disable_echolink");
}



// Playlist management

function addFileToPlaylist() {
    var name = Math.floor((Math.random() * 100000));

    var code = '<div class="dropdown playlist-item"> \
                    <button class="btn btn-default dropdown-toggle" type="button" id="' + name + '" data-toggle="dropdown" aria-haspopup="true" aria-expanded="true"> \
                        <span class="selected-filename">Select file for playback</span>\
                        <span class="caret"></span>\
                    </button>\
                    <ul class="dropdown-menu" aria-labelledby="' + name + '">\
                    </ul>\
                    <div class="glyphicon glyphicon-remove playlist-remove"></div>\
                </div>\
                \
                <div class="vertical-spacer-small playlist-spacer"></div>';
    var el = $(code);
    addFilesForUl(el.children("ul")[0]);
    $("#add-file").before(el);
}

function addGapToPlaylist() {
    var code = '<div class="gap playlist-item">\
                <input type="text" class="gap form-control" placeholder="Enter pause in seconds"></input>\
                    <div class="glyphicon glyphicon-remove playlist-remove" style="display: inline-block"></div>\
                </div>\
                <div class="vertical-spacer-small playlist-spacer"></div>';
    // todo set <li>s correctly
    $("#add-file").before($(code));
}

function addInetOnToPlaylist() {
    var code = '<div class="inet-on playlist-item">\
                <i>IRLP and Echolink become enabled</i>\
                <div class="glyphicon glyphicon-remove playlist-remove"></div>\
                </div>\
                <div class="vertical-spacer-small playlist-spacer"></div>';
    $("#add-file").before($(code));
}

function addInetOffToPlaylist() {
    var code = '<div class="inet-off playlist-item">\
                <i>IRLP and Echolink become disabled</i>\
                <div class="glyphicon glyphicon-remove playlist-remove"></div>\
                </div>\
                <div class="vertical-spacer-small playlist-spacer"></div>';
    $("#add-file").before($(code));
}

function removeItemFromPlaylist(ev) {
    var el = ev.target;
    $(el).parent().next().remove();
    $(el).parent().remove();
}

function updateFilesCache() {
    $.ajax("/schedule/files").done(function(data, status, jqXHR) {
        files_cache = JSON.parse(data)
        updateFilesInFields();
    });
}

function updateFilesInFields() {
    $("li.filename").remove();
    $("ul.dropdown-menu").each(function(ul) {
        addFilesForUl(ul);
    });
}

function addFilesForUl(ul) {
    for (var i = 0; i < files_cache.length; i++)
    {
        var f = files_cache[i];
        var html = '<li class="filename"><a href="#" onclick="chooseFile(this, \'' + f + '\')">' + f + '</a></li>';
        $(html).prependTo(ul);
    }
}

function submitPlaylist() {

    var itemFilenames = []

    $(document).find(".playlist-item").each(function(index, i) {
        console.log(i)
        if ($(i).hasClass("dropdown")) {
            itemFilenames.push($(i).find(".selected-filename").text());
        }
        else if ($(i).hasClass("inet-on")) {
            itemFilenames.push(':INETON:');
        }
        else if ($(i).hasClass("inet-off")) {
            itemFilenames.push(':INETOFF:');
        }
        else {
            itemFilenames.push(":GAP:" + $(i).find("input").val());
        }
    });

    var date = $("#new-schedule-date").val();
    var time = $("#new-schedule-time").val();

    // Should validate and maybe show an error instead of hiding

    var new_schedule = {};
    new_schedule.playlist = itemFilenames;
    new_schedule.date = date;
    new_schedule.time = time;

    $.post("/schedule/new", JSON.stringify(new_schedule), function(data, status) {
        refreshSchedules();
    });
    $("#testmodal").modal('hide');
}

function refreshSchedules() {
    $.ajax("/schedule/list").done(function(data, status, jqXHR) {
        var list = JSON.parse(data)
        clearSchedules();
        renderSchedules(list);
    });
}

function clearSchedules() {
    $("#schedule-table").find("tr.schedule-item").remove();
}

function renderSchedules(list) {
    for (var i = 0; i < list.length; i++) {
        var entry = list[i];
        var timestamp = entry["timestamp_string"];
        var identifier = entry["identifier"];
        var playlist = entry["playlist"];
        var playlist_html = "<ul>\n";
        for (var p = 0; p < playlist.length; p++) {
            var p_entry = playlist[p];
            playlist_html += "<li>" + p_entry + "</li>\n";
        }
        playlist_html += "</ul>\n";
        var code = '<tr class="schedule-item">\
                <td>' + timestamp + '</td>\
                <td>' + playlist_html + '</td>\
                <td>\
                    <a href="#" onclick="confirmDeleteSchedule(\'' + identifier + '\')">\
                    <div class="glyphicon glyphicon-remove"></div>\
                    </a>\
                </td>\
            </tr>';
        $(code).appendTo("#schedule-table");
    }
}

function confirmDeleteSchedule(item) {
    bootbox.confirm("Are you sure you want to delete this schedule?", function(result) {
        if (result) {
            $.post("/schedule/delete", item, function(data, status) {
                console.log("HELLO");
                refreshSchedules();
            });
        }
    });
}
