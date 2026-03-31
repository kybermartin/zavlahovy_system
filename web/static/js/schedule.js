// web/static/js/schedule.js
// JavaScript pre stránku plánov

$(document).ready(function() {
    loadSchedule();
    setupEventListeners();
    updateDateTime();
    setInterval(updateDateTime, 1000);
});

function updateDateTime() {
    const now = new Date();
    const datetime = now.toLocaleDateString('sk-SK') + ' ' + 
                    now.toLocaleTimeString('sk-SK', {hour: '2-digit', minute: '2-digit', second: '2-digit'});
    $('#current-datetime').text(datetime);
}

function setupEventListeners() {
    // Zmena aktívneho stavu
    $('.interval-active').change(function() {
        const id = $(this).data('id');
        updateIntervalPreview(id);
        updateCardOpacity(id);
    });

    // Zmena času
    $('.interval-start, .interval-stop').change(function() {
        const id = $(this).data('id');
        updateIntervalPreview(id);
        checkTimeOrder(id);
    });

    // Zmena okruhu
    $('.interval-okruh').change(function() {
        const id = $(this).data('id');
        updateIntervalPreview(id);
    });

    // Zmena tlaku
    $('.interval-pressure').on('input', function() {
        const id = $(this).data('id');
        const value = $(this).val();
        $(`#pressure${id}`).text(value + '%');
        updateIntervalPreview(id);
    });

    // Tlačidlá
    $('#saveSchedule').click(saveSchedule);
    $('#saveAllBtn').click(saveSchedule);
    $('#resetSchedule').click(resetToDefault);
    $('#checkConflicts').click(checkConflicts);

    // Modal close
    $('.close').click(function() {
        $('#conflictModal').hide();
    });

    $(window).click(function(event) {
        if ($(event.target).is('#conflictModal')) {
            $('#conflictModal').hide();
        }
    });
}

function loadSchedule() {
    showLoader();
    
    $.ajax({
        url: '/api/schedule',
        method: 'GET',
        dataType: 'json',
        success: function(data) {
            if (data.intervals) {
                data.intervals.forEach(interval => {
                    updateFormFromInterval(interval);
                });
            }
            hideLoader();
        },
        error: function(xhr, status, error) {
            console.error('Chyba pri načítaní plánu:', error);
            showNotification('Nepodarilo sa načítať plán', 'error');
            hideLoader();
        }
    });
}

function updateFormFromInterval(interval) {
    const id = interval.id;
    
    $(`.interval-active[data-id="${id}"]`).prop('checked', interval.aktivny);
    $(`.interval-start[data-id="${id}"]`).val(interval.start);
    $(`.interval-stop[data-id="${id}"]`).val(interval.stop);
    $(`.interval-okruh[data-id="${id}"]`).val(interval.okruh);
    $(`.interval-pressure[data-id="${id}"]`).val(interval.tlak);
    $(`#pressure${id}`).text(interval.tlak + '%');
    
    updateIntervalPreview(id);
    updateCardOpacity(id);
}

function updateIntervalPreview(id) {
    const active = $(`.interval-active[data-id="${id}"]`).is(':checked');
    const start = $(`.interval-start[data-id="${id}"]`).val();
    const stop = $(`.interval-stop[data-id="${id}"]`).val();
    const okruh = $(`.interval-okruh[data-id="${id}"]`).val();
    const tlak = $(`.interval-pressure[data-id="${id}"]`).val();
    
    let previewText = '';
    if (active) {
        previewText = `${start} - ${stop} | Okruh ${okruh} | ${tlak}%`;
    } else {
        previewText = 'Interval je neaktívny';
    }
    
    $(`#preview${id} .preview-text`).text(previewText);
    
    // Aktualizácia tabuľky
    updateScheduleTable();
}

function updateCardOpacity(id) {
    const active = $(`.interval-active[data-id="${id}"]`).is(':checked');
    if (active) {
        $(`#interval${id}`).removeClass('inactive');
    } else {
        $(`#interval${id}`).addClass('inactive');
    }
}

function checkTimeOrder(id) {
    const start = $(`.interval-start[data-id="${id}"]`).val();
    const stop = $(`.interval-stop[data-id="${id}"]`).val();
    
    if (start && stop && start >= stop) {
        showNotification('Čas ukončenia musí byť neskôr ako čas štartu!', 'warning');
        $(`.interval-stop[data-id="${id}"]`).addClass('error');
    } else {
        $(`.interval-stop[data-id="${id}"]`).removeClass('error');
    }
}

function saveSchedule() {
    const intervals = [];
    
    for (let i = 1; i <= 4; i++) {
        intervals.push({
            id: i,
            aktivny: $(`.interval-active[data-id="${i}"]`).is(':checked'),
            start: $(`.interval-start[data-id="${i}"]`).val(),
            stop: $(`.interval-stop[data-id="${i}"]`).val(),
            okruh: parseInt($(`.interval-okruh[data-id="${i}"]`).val()),
            tlak: parseInt($(`.interval-pressure[data-id="${i}"]`).val())
        });
    }
    
    // Validácia
    for (let interval of intervals) {
        if (interval.aktivny) {
            if (!interval.start || !interval.stop) {
                showNotification(`Interval ${interval.id}: Vyplňte časy`, 'error');
                return;
            }
            if (interval.start >= interval.stop) {
                showNotification(`Interval ${interval.id}: Čas ukončenia musí byť neskôr`, 'error');
                return;
            }
        }
    }
    
    showLoader();
    
    $.ajax({
        url: '/api/schedule',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ intervals: intervals }),
        success: function(response) {
            hideLoader();
            showNotification('Plán bol úspešne uložený', 'success');
            updateScheduleTable();
        },
        error: function(xhr, status, error) {
            hideLoader();
            const response = xhr.responseJSON;
            if (response && response.messages) {
                response.messages.forEach(msg => showNotification(msg, 'error'));
            } else {
                showNotification('Chyba pri ukladaní plánu', 'error');
            }
        }
    });
}

function resetToDefault() {
    if (confirm('Naozaj chcete obnoviť predvolené nastavenia?')) {
        const defaultIntervals = [
            { id: 1, start: '06:00', stop: '06:30', okruh: 1, tlak: 80, aktivny: true },
            { id: 2, start: '18:00', stop: '18:30', okruh: 2, tlak: 70, aktivny: true },
            { id: 3, start: '12:00', stop: '12:30', okruh: 1, tlak: 50, aktivny: false },
            { id: 4, start: '15:00', stop: '15:30', okruh: 4, tlak: 60, aktivny: false }
        ];
        
        defaultIntervals.forEach(interval => updateFormFromInterval(interval));
        showNotification('Predvolené nastavenia obnovené', 'success');
    }
}

function checkConflicts() {
    const intervals = [];
    
    for (let i = 1; i <= 4; i++) {
        if ($(`.interval-active[data-id="${i}"]`).is(':checked')) {
            intervals.push({
                id: i,
                start: $(`.interval-start[data-id="${i}"]`).val(),
                stop: $(`.interval-stop[data-id="${i}"]`).val()
            });
        }
    }
    
    const conflicts = [];
    
    // Kontrola prekrývania
    for (let i = 0; i < intervals.length; i++) {
        for (let j = i + 1; j < intervals.length; j++) {
            if (intervals[i].start < intervals[j].stop && intervals[j].start < intervals[i].stop) {
                conflicts.push(`Interval ${intervals[i].id} a ${intervals[j].id} sa prekrývajú`);
            }
        }
    }
    
    if (conflicts.length > 0) {
        $('#conflictMessage').html(conflicts.join('<br>'));
        $('#conflictModal').show();
    } else {
        showNotification('Žiadne kolízie nájdené', 'success');
    }
}

function updateScheduleTable() {
    const tbody = $('#scheduleTableBody');
    tbody.empty();
    
    for (let i = 1; i <= 4; i++) {
        const active = $(`.interval-active[data-id="${i}"]`).is(':checked');
        const start = $(`.interval-start[data-id="${i}"]`).val();
        const stop = $(`.interval-stop[data-id="${i}"]`).val();
        const okruh = $(`.interval-okruh[data-id="${i}"]`).val();
        const tlak = $(`.interval-pressure[data-id="${i}"]`).val();
        
        let row = '<tr>';
        row += `<td>${i}</td>`;
        row += `<td>${active ? start + ' - ' + stop : '--:-- - --:--'}</td>`;
        row += `<td>${active ? 'Okruh ' + okruh : '-'}</td>`;
        row += `<td>${active ? tlak + '%' : '-'}</td>`;
        row += `<td><span class="badge ${active ? 'badge-success' : 'badge-inactive'}">${active ? 'Aktívny' : 'Neaktívny'}</span></td>`;
        row += '</tr>';
        
        tbody.append(row);
    }
}

function showNotification(message, type = 'info') {
    // Jednoduchá notifikácia
    const notification = $('<div class="notification"></div>')
        .text(message)
        .addClass(type);
    
    $('body').append(notification);
    
    setTimeout(() => {
        notification.fadeOut(() => notification.remove());
    }, 3000);
}

function showLoader() {
    if ($('#loader').length === 0) {
        $('body').append('<div id="loader" class="loader"></div>');
    }
}

function hideLoader() {
    $('#loader').remove();
}