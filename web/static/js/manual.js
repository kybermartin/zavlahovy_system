// web/static/js/manual.js
// JavaScript pre manuálne ovládanie

// Globálne premenné pre dialog
let pendingAction = null;

$(document).ready(function() {
    loadInitialState();
    setupEventListeners();
	setupModalListeners();
    updateDateTime();
    setInterval(updateDateTime, 1000);
    setInterval(updateSystemStatus, 2000);
});

let currentState = {
    tlakove: { mode: 'auto', state: 'off' },
    nasavacie: { mode: 'auto', state: 'off' },
    ventily: [
        { id: 1, pozicia: 0, otvoreny: false },
        { id: 2, pozicia: 0, otvoreny: false },
        { id: 3, pozicia: 0, otvoreny: false },
        { id: 4, pozicia: 0, otvoreny: false }
    ],
    senzory: {
        spodny: false,
        horny: false
    }
};

function setupModalListeners(){
	$('#confirmYes').click(function() {
        if (pendingAction) {
            pendingAction();
        }
        hideConfirm();
    });
    
    $('#confirmNo, .modal-close').click(hideConfirm);
    
    $('#confirmDialog').click(function(e) {
        if ($(e.target).is('#confirmDialog')) {
            hideConfirm();
        }
    });
    
    $(document).keydown(function(e) {
        if (e.key === 'Escape' && $('#confirmDialog').is(':visible')) {
            hideConfirm();
        }
    });
}


function setupEventListeners() {
    // Režimy čerpadiel
    $('.mode-btn').click(function() {
        const pump = $(this).data('pump');
        const mode = $(this).data('mode');
        
        // Odstrániť active z ostatných tlačidiel pre dané čerpadlo
        $(`.mode-btn[data-pump="${pump}"]`).removeClass('active');
        $(this).addClass('active');
        
        // Zavolať API pre zmenu režimu
        setPumpMode(pump, mode);
    });

    // Manuálne ovládanie čerpadiel
    $('#tlakove-start').click(function() {
        if (!$(this).prop('disabled')) {
            showConfirm('Spustiť tlakové čerpadlo?', function() {
                controlPump('tlakove', 'start');
            });
        }
    });

    $('#tlakove-stop').click(function() {
        if (!$(this).prop('disabled')) {
            showConfirm('Zastaviť tlakové čerpadlo?', function() {
                controlPump('tlakove', 'stop');
            });
        }
    });

    $('#nasavacie-start').click(function() {
        if (!$(this).prop('disabled')) {
            showConfirm('Spustiť nasávacie čerpadlo?', function() {
                controlPump('nasavacie', 'start');
            });
        }
    });

    $('#nasavacie-stop').click(function() {
        if (!$(this).prop('disabled')) {
            showConfirm('Zastaviť nasávacie čerpadlo?', function() {
                controlPump('nasavacie', 'stop');
            });
        }
    });

    // Ovládanie ventilov
    $('.valve-open').click(function() {
        const valveId = $(this).data('valve');
        const pressure = $(`#valve${valveId}-pressure`).val();
        
        showConfirm(`Otvoriť ventil ${valveId} s tlakom ${pressure}%?`, function() {
            controlValve(valveId, 'open', pressure);
        });
    });

    $('.valve-close').click(function() {
        const valveId = $(this).data('valve');
        
        showConfirm(`Zatvoriť ventil ${valveId}?`, function() {
            controlValve(valveId, 'close', 0);
        });
    });

    // Posuvníky tlaku
    $('.valve-pressure-slider').on('input', function() {
        const valveId = this.id.replace('valve', '').replace('-pressure', '');
        const value = $(this).val();
        $(`#valve${valveId}-pressure-value`).text(value + '%');
    });

    // Rýchle predvoľby
    $('.preset-btn[data-okruh]').click(function() {
        const okruh = $(this).data('okruh');
        const tlak = $(this).data('tlak');
        
        if (currentState.tlakove.mode === 'manual') {
            showConfirm(`Spustiť okruh ${okruh} s tlakom ${tlak}%?`, function() {
                controlPump('tlakove', 'start', okruh, tlak);
            });
        } else {
            showNotification('Čerpadlo je v AUTO režime. Prepnite na MANUÁL.', 'warning');
        }
    });

    $('#vsetky-ventily-otvor').click(function() {
        if (currentState.tlakove.mode === 'manual') {
            showConfirm('Otvoriť všetky ventily na 50%?', function() {
                for (let i = 1; i <= 4; i++) {
                    setTimeout(() => {
                        controlValve(i, 'open', 50);
                    }, i * 500);
                }
            });
        }
    });

    $('#vsetky-ventily-zatvor').click(function() {
        showConfirm('Zatvoriť všetky ventily?', function() {
            for (let i = 1; i <= 4; i++) {
                setTimeout(() => {
                    controlValve(i, 'close', 0);
                }, i * 300);
            }
        });
    });

    // Núdzové ovládanie
    $('#emergencyStopAll').click(function() {
        showConfirm('🚨 NAOZAJ chcete núdzovo zastaviť VŠETKO?', function() {
            emergencyStop();
        }, true);
    });

    $('#resetSystem').click(function() {
        showConfirm('Reštartovať systém?', function() {
            resetSystem();
        });
    });
}

function loadInitialState() {
    showLoader();
    
    $.ajax({
        url: '/api/status',
        method: 'GET',
        dataType: 'json',
        success: function(data) {
            updateUIFromData(data);
            hideLoader();
        },
        error: function(xhr, status, error) {
            console.error('Chyba pri načítaní stavu:', error);
            showNotification('Nepodarilo sa načítať stav systému', 'error');
            hideLoader();
        }
    });
}

function updateSystemStatus() {
    $.ajax({
        url: '/api/status',
        method: 'GET',
        dataType: 'json',
        success: function(data) {
            updateUIFromData(data);
        },
        error: function(xhr, status, error) {
            console.error('Chyba pri aktualizácii stavu:', error);
        }
    });
}

function updateUIFromData(data) {
    // Aktualizácia stavových premenných
    currentState.tlakove = data.tlakove;
    currentState.nasavacie = data.nasavacie;
    currentState.ventily = data.ventily;
    
    // Aktualizácia režimov
    updateModeButtons('tlakove', data.tlakove.mode);
    updateModeButtons('nasavacie', data.nasavacie.mode);
    
    // Aktualizácia tlakového čerpadla
    updatePumpUI('tlakove', data.tlakove);
    
    // Aktualizácia nasávacieho čerpadla
    updatePumpUI('nasavacie', data.nasavacie);
    
    // Aktualizácia ventilov
    data.ventily.forEach(valve => {
        updateValveUI(valve);
    });
    
    // Aktualizácia senzorov (ak sú v dátach)
    if (data.senzory) {
        updateSensorsUI(data.senzory);
    }
    
    // Aktualizácia poslednej akcie
    $('#last-action').text(new Date().toLocaleTimeString('sk-SK'));
}

function updateModeButtons(pump, mode) {
    $(`.mode-btn[data-pump="${pump}"]`).removeClass('active');
    $(`.mode-btn[data-pump="${pump}"][data-mode="${mode.toLowerCase()}"]`).addClass('active');
}

function updatePumpUI(pump, data) {
    const isOn = data.state === 'BEZI';
    const isAuto = data.mode === 'AUTO';
    
    // LED indikátor
    $(`#${pump}-led`)
        .removeClass('on off')
        .addClass(isOn ? 'on' : 'off');
    
    // Text stavu
    $(`#${pump}-state`).text(isOn ? 'Beží' : 'Vypnuté');
    
    // Povolenie/zakázanie tlačidiel
    if (isAuto) {
        $(`#${pump}-start, #${pump}-stop`).prop('disabled', true);
        $(`.valve-open, .valve-close, .valve-pressure-slider`).prop('disabled', true);
    } else {
        $(`#${pump}-start, #${pump}-stop`).prop('disabled', false);
        $(`.valve-open, .valve-close, .valve-pressure-slider`).prop('disabled', false);
    }
}

function updateValveUI(valve) {
    const id = valve.okruh;
    const isOpen = valve.otvoreny;
    const pozicia = valve.pozicia;
    
    // Status badge
    $(`#valve${id}-status`)
        .removeClass('open closed')
        .addClass(isOpen ? 'open' : 'closed')
        .text(isOpen ? 'Otvorený' : 'Zatvorený');
    
    // Posuvník
    $(`#valve${id}-pressure`).val(pozicia);
    $(`#valve${id}-pressure-value`).text(pozicia + '%');
    
    // Tlakový indikátor
    $(`#valve${id}-bar`).css('width', pozicia + '%');
    
    // Farba karty
    if (isOpen) {
        $(`#valve${id}`).css('border-left', '4px solid #48bb78');
    } else {
        $(`#valve${id}`).css('border-left', '4px solid #cbd5e0');
    }
}

function updateSensorsUI(senzory) {
    // Spodný senzor
    const spodnyWet = senzory.spodny;
    $('#spodny-senzor')
        .text(spodnyWet ? 'MOKRÝ' : 'SUCHÝ')
        .removeClass('wet dry')
        .addClass(spodnyWet ? 'wet' : 'dry');
    
    // Horný senzor
    const hornyWet = senzory.horny;
    $('#horny-senzor')
        .text(hornyWet ? 'MOKRÝ' : 'SUCHÝ')
        .removeClass('wet dry')
        .addClass(hornyWet ? 'wet' : 'dry');
    
    // Výpočet hladiny (aproximácia)
    let level = 0;
    if (hornyWet) level = 100;
    else if (spodnyWet) level = 50;
    else level = 0;
    
    $('#water-level-fill').css('height', level + '%');
}

function setPumpMode(pump, mode) {
    showLoader();
    
    $.ajax({
        url: '/api/control/pump',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            pump: pump,
            action: 'mode',
            auto: mode === 'auto'
        }),
        success: function(response) {
            hideLoader();
            showNotification(`Čerpadlo prepnuté na ${mode === 'auto' ? 'AUTO' : 'MANUÁL'}`, 'success');
            loadInitialState(); // Znovu načítať stav
        },
        error: function(xhr, status, error) {
            hideLoader();
            showNotification('Chyba pri zmene režimu', 'error');
        }
    });
}

function controlPump(pump, action, okruh = null, tlak = null) {
    showLoader();
    
    const data = {
        pump: pump,
        action: action
    };
    
    if (okruh) data.okruh = okruh;
    if (tlak) data.tlak = tlak;
    
    $.ajax({
        url: '/api/control/pump',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(data),
        success: function(response) {
            hideLoader();
            showNotification(`Príkaz vykonaný`, 'success');
            loadInitialState();
        },
        error: function(xhr, status, error) {
            hideLoader();
            showNotification('Chyba pri ovládaní čerpadla', 'error');
        }
    });
}

function controlValve(valveId, action, pressure) {
    showLoader();
    
    $.ajax({
        url: '/api/control/valve',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            okruh: parseInt(valveId),
            action: action,
            tlak: parseInt(pressure)
        }),
        success: function(response) {
            hideLoader();
            showNotification(`Ventil ${valveId} ${action === 'open' ? 'otvorený' : 'zatvorený'}`, 'success');
            loadInitialState();
        },
        error: function(xhr, status, error) {
            hideLoader();
            showNotification('Chyba pri ovládaní ventilu', 'error');
        }
    });
}

function emergencyStop() {
    showLoader();
    
    // Postupne zastaviť všetko
    Promise.all([
        $.ajax({ url: '/api/control/pump', method: 'POST', data: JSON.stringify({ pump: 'tlakove', action: 'stop' }), contentType: 'application/json' }),
        $.ajax({ url: '/api/control/pump', method: 'POST', data: JSON.stringify({ pump: 'nasavacie', action: 'stop' }), contentType: 'application/json' })
    ]).then(() => {
        // Zatvoriť všetky ventily
        for (let i = 1; i <= 4; i++) {
            $.ajax({
                url: '/api/control/valve',
                method: 'POST',
                data: JSON.stringify({ okruh: i, action: 'close' }),
                contentType: 'application/json'
            });
        }
        
        hideLoader();
        showNotification('🚨 NÚDZOVÉ ZASTAVENIE vykonané', 'warning');
        loadInitialState();
    }).catch(() => {
        hideLoader();
        showNotification('Chyba pri núdzovom zastavení', 'error');
    });
}

function resetSystem() {
    showConfirm('Naozaj reštartovať systém?', function() {
        showNotification('Reštartujem systém...', 'info');
        setTimeout(() => {
            window.location.reload();
        }, 2000);
    });
}

function updateDateTime() {
    const now = new Date();
    const datetime = now.toLocaleDateString('sk-SK') + ' ' + 
                    now.toLocaleTimeString('sk-SK', {hour: '2-digit', minute: '2-digit', second: '2-digit'});
    $('#current-datetime').text(datetime);
    $('#current-time').text(now.toLocaleTimeString('sk-SK'));
}

// Funkcia pre zobrazenie potvrdzovacieho dialógu
function showConfirm(message, callback, isEmergency = false) {
    pendingAction = callback;
    
    const $modal = $('#confirmDialog');
    const $message = $('#confirmMessage');
    const $container = $modal.find('.modal-container');
    
    $message.text(message);
    
    if (isEmergency) {
        $message.addClass('emergency');
        $container.addClass('emergency');
    } else {
        $message.removeClass('emergency');
        $container.removeClass('emergency');
    }
    
    $modal.css('display', 'flex');
    $('body').css('overflow', 'hidden');
}

// Funkcia pre skrytie dialógu
function hideConfirm() {
    $('#confirmDialog').hide();
    $('body').css('overflow', '');
    pendingAction = null;
}

// Potvrdenie akcie
function confirmAction() {
    if (pendingAction) {
        pendingAction();
    }
    hideConfirm();
}

function showNotification(message, type = 'info') {
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