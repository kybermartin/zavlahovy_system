// web/static/js/settings.js
// JavaScript pre stránku nastavení

// Globálne premenné pre dialog
let pendingAction = null;

$(document).ready(function() {
    loadSettings();
    // Načítanie stavu auto‑startu
    loadAutoStartStatus();

    setupEventListeners();
	setupModalListeners();
    updateDateTime();
    setInterval(updateDateTime, 1000);
    setInterval(updateSystemInfo, 5000);
});

let settingsCache = {};

function setupEventListeners() {
    // Časové nastavenia
    $('#set-time').click(setSystemTime);
    $('#sync-rtc').click(syncRTC);
    
    // Posuvníky
    $('#lcd-brightness').on('input', function() {
        $('#brightness-value').text($(this).val() + '%');
    });
    
    $('#lcd-contrast').on('input', function() {
        $('#contrast-value').text($(this).val() + '%');
    });
    
    // Test serv
    $('.test-servo').click(function() {
        const servoId = $(this).data('servo');
        testServo(servoId);
    });
    
    // Test LCD
    $('#test-lcd').click(testLCD);
    
    // Export/Import
    $('#export-settings').click(exportSettings);
    $('#import-settings').click(() => $('#import-file').click());
    $('#import-file').change(importSettings);
    $('#reset-to-defaults').click(resetToDefaults);

    
    // Systémové akcie
    $('#auto-start').change(function() {
        const value = $(this).val();
        saveAutoStartSetting(value);
    });
    $('#restart-app').click(() => showConfirm('Reštartovať aplikáciu?', restartApp));
    $('#shutdown-pi').click(() => showConfirm('VYPNOŤ Raspberry Pi?', shutdownPi, true));
    $('#reboot-pi').click(() => showConfirm('REŠTARTOVAŤ Raspberry Pi?', rebootPi, true));
    
    // Uloženie
    $('#save-all-settings').click(saveAllSettings);
    
}


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

function loadSettings() {
    showLoader();

    // Načítanie času a RTC stavu
    $.ajax({
        url: '/api/time',
        method: 'GET',
        dataType: 'json',
        success: function(data) {
            $('#current-system-time').text(data.datetime);
            $('#timezone-info').text(`${data.timezone} (UTC${data.utc_offset >= 0 ? '+' : ''}${data.utc_offset})`);
            $('#is-dst').text(data.is_dst ? 'Áno (letný čas)' : 'Nie (zimný čas)');
            
            // Zobrazenie RTC stavu
            if (data.rtc && data.rtc.connected) {
                $('#rtc-status').html('<span class="status-ok">✅ Pripojený</span>');
                $('#rtc-device').text(data.rtc.device || '/dev/rtc0');
            } else {
                $('#rtc-status').html('<span class="status-error">❌ Nepripojený</span>');
                $('#rtc-device').text('-');
            }
        },
        error: function() {
            $('#current-system-time').text('Chyba načítania');
        }
    });
    
    // Načítanie RTC detailov
    $.ajax({
        url: '/api/rtc/status',
        method: 'GET',
        dataType: 'json',
        success: function(data) {
            if (data.connected) {
                $('#rtc-time').text(data.local || data.utc || '---');
            } else {
                $('#rtc-time').text('Nedostupný');
            }
        }
    });
    
    // Načítať nastavenia z API
    $.ajax({
        url: '/api/settings',
        method: 'GET',
        dataType: 'json',
        success: function(data) {
            settingsCache = data;
            updateUIFromSettings(data);
            hideLoader();
            showNotification('Nastavenia načítané', 'success');
        },
        error: function(xhr, status, error) {
            console.error('Chyba pri načítaní nastavení:', error);
            loadDefaultSettings(); // Pre vývoj načítať demo dáta
            hideLoader();
        }
    });
}

function loadDefaultSettings() {
    // Demo dáta pre vývoj bez backendu
    const defaultSettings = {
        time: {
            current: new Date().toISOString().slice(0, 19).replace('T', ' '),
            timezone: 'Europe/Bratislava',
            rtc_status: 'pripojený',
            rtc_time: new Date().toISOString().slice(0, 19).replace('T', ' ')
        },
        pumps: {
            tlakove_auto: true,
            tlakove_delay: 2,
            nasavacie_auto: true,
            dry_run: true,
            dry_run_delay: 30,
            sensor_type: 'NO'
        },
        servos: {
            servo1: { closed: 2.5, open: 12.5 },
            servo2: { closed: 2.5, open: 12.5 },
            servo3: { closed: 2.5, open: 12.5 },
            servo4: { closed: 2.5, open: 12.5 }
        },
        lcd: {
            brightness: 80,
            contrast: 50,
            backlight: true
        },
        network: {
            port: 5000,
            remote_access: false,
            ip: '192.168.1.100',
            mac: 'b8:27:eb:12:34:56',
            hostname: 'zavlahovy-system'
        },
        system: {
            log_level: 'INFO',
            auto_start: 'yes',
            version: '1.0.0',
            python_version: '3.9.2',
            flask_version: '2.0.1',
            uptime: '2 dni 5 hodín',
            cpu_temp: '45.5°C',
            free_ram: '512 MB',
            free_disk: '8.2 GB'
        }
    };
    
    settingsCache = defaultSettings;
    updateUIFromSettings(defaultSettings);
}

function updateUIFromSettings(data) {
    // Čas
    $('#current-system-time').text(data.time.current || '---');
    $('#timezone').val(data.time.timezone || 'Europe/Bratislava');
    $('#rtc-status').text(data.time.rtc_status || '---');
    $('#rtc-time').text(data.time.rtc_time || '---');
    
    // Čerpadlá
    $('#tlakove-auto-mode').prop('checked', data.pumps.tlakove_auto);
    $('#tlakove-start-delay').val(data.pumps.tlakove_delay);
    $('#nasavacie-auto-mode').prop('checked', data.pumps.nasavacie_auto);
    $('#dry-run-protection').prop('checked', data.pumps.dry_run);
    $('#dry-run-delay').val(data.pumps.dry_run_delay);
    $('#sensor-type').val(data.pumps.sensor_type);
    
    // Servá
    $('#servo1-closed').val(data.servos.servo1.closed);
    $('#servo1-open').val(data.servos.servo1.open);
    $('#servo2-closed').val(data.servos.servo2.closed);
    $('#servo2-open').val(data.servos.servo2.open);
    $('#servo3-closed').val(data.servos.servo3.closed);
    $('#servo3-open').val(data.servos.servo3.open);
    $('#servo4-closed').val(data.servos.servo4.closed);
    $('#servo4-open').val(data.servos.servo4.open);
    
    // LCD
    $('#lcd-brightness').val(data.lcd.brightness);
    $('#brightness-value').text(data.lcd.brightness + '%');
    $('#lcd-contrast').val(data.lcd.contrast);
    $('#contrast-value').text(data.lcd.contrast + '%');
    $('#lcd-backlight').prop('checked', data.lcd.backlight);
    
    // Sieť
    $('#web-port').val(data.network.port);
    $('#remote-access').prop('checked', data.network.remote_access);
    $('#ip-address').text(data.network.ip);
    $('#mac-address').text(data.network.mac);
    $('#hostname').text(data.network.hostname);
    
    // Systém
    $('#log-level').val(data.system.log_level);
    $('#auto-start').val(data.system.auto_start);
    $('#system-version').text(data.system.version);
    $('#python-version').text(data.system.python_version);
    $('#flask-version').text(data.system.flask_version);
    $('#uptime').text(data.system.uptime);
    $('#cpu-temp').text(data.system.cpu_temp);
    $('#free-ram').text(data.system.free_ram);
    $('#free-disk').text(data.system.free_disk);
}

function updateSystemInfo() {
    $.ajax({
        url: '/api/system/info',
        method: 'GET',
        dataType: 'json',
        success: function(data) {
            $('#uptime').text(data.uptime);
            $('#cpu-temp').text(data.cpu_temp);
            $('#free-ram').text(data.free_ram);
            $('#free-disk').text(data.free_disk);
            $('#ip-address').text(data.ip);
        },
        error: function() {
            // Ignorovať chyby pri aktualizácii
        }
    });
}

function setSystemTime() {
    const timeStr = $('#manual-time').val();
    if (!timeStr) {
        showNotification('Vyberte čas', 'warning');
        return;
    }
    
    // Konverzia na správny formát
    const dateTime = timeStr.replace('T', ' ') + ':00';
    
    showLoader();
    
    $.ajax({
        url: '/api/time',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({ time: dateTime }),
        success: function(response) {
            hideLoader();
            showNotification('Čas nastavený', 'success');
            loadSettings(); // Znovu načítať
        },
        error: function(xhr, status, error) {
            hideLoader();
            showNotification('Chyba pri nastavení času', 'error');
        }
    });
}

function syncRTC() {
    showConfirm('Synchronizovať RTC s časom RPi?', function() {
        showLoader();
        
        $.ajax({
            url: '/api/rtc/sync',
            method: 'POST',
            success: function(response) {
                hideLoader();
                showNotification('RTC synchronizované', 'success');
                loadSettings();
            },
            error: function() {
                hideLoader();
                showNotification('Chyba pri synchronizácii RTC', 'error');
            }
        });
    });
}

function testServo(servoId) {
    const closed = $(`#servo${servoId}-closed`).val();
    const open = $(`#servo${servoId}-open`).val();
    
    showConfirm(`Test serva ${servoId}?\nZatvorené: ${closed}%, Otvorené: ${open}%`, function() {
        showLoader();
        
        $.ajax({
            url: '/api/servo/test',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                servo: servoId,
                closed: parseFloat(closed),
                open: parseFloat(open)
            }),
            success: function(response) {
                hideLoader();
                showNotification(`Servo ${servoId} test OK`, 'success');
            },
            error: function() {
                hideLoader();
                showNotification(`Chyba pri teste serva ${servoId}`, 'error');
            }
        });
    });
}

function testLCD() {
    const line1 = $('#lcd-test-line1').val() || 'Test LCD';
    const line2 = $('#lcd-test-line2').val() || 'Zavlahovy system';
    
    $.ajax({
        url: '/api/lcd/test',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            line1: line1,
            line2: line2
        }),
        success: function() {
            showNotification('Testovacia správa zobrazená', 'success');
        },
        error: function() {
            showNotification('Chyba pri teste LCD', 'error');
        }
    });
}

function saveAllSettings() {
    const settings = {
        pumps: {
            tlakove_auto: $('#tlakove-auto-mode').is(':checked'),
            tlakove_delay: parseInt($('#tlakove-start-delay').val()),
            nasavacie_auto: $('#nasavacie-auto-mode').is(':checked'),
            dry_run: $('#dry-run-protection').is(':checked'),
            dry_run_delay: parseInt($('#dry-run-delay').val()),
            sensor_type: $('#sensor-type').val()
        },
        servos: {
            servo1: {
                closed: parseFloat($('#servo1-closed').val()),
                open: parseFloat($('#servo1-open').val())
            },
            servo2: {
                closed: parseFloat($('#servo2-closed').val()),
                open: parseFloat($('#servo2-open').val())
            },
            servo3: {
                closed: parseFloat($('#servo3-closed').val()),
                open: parseFloat($('#servo3-open').val())
            },
            servo4: {
                closed: parseFloat($('#servo4-closed').val()),
                open: parseFloat($('#servo4-open').val())
            }
        },
        lcd: {
            brightness: parseInt($('#lcd-brightness').val()),
            contrast: parseInt($('#lcd-contrast').val()),
            backlight: $('#lcd-backlight').is(':checked')
        },
        network: {
            port: parseInt($('#web-port').val()),
            remote_access: $('#remote-access').is(':checked')
        },
        system: {
            log_level: $('#log-level').val(),
            auto_start: $('#auto-start').val()
        }
    };
    
    showLoader();
    
    $.ajax({
        url: '/api/settings',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(settings),
        success: function(response) {
            hideLoader();
            $('#save-status').text('✓ Uložené ' + new Date().toLocaleTimeString()).fadeIn().delay(3000).fadeOut();
            showNotification('Nastavenia uložené', 'success');
            settingsCache = settings;
        },
        error: function(xhr, status, error) {
            hideLoader();
            showNotification('Chyba pri ukladaní', 'error');
        }
    });
}

function exportSettings() {
    const dataStr = JSON.stringify(settingsCache, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    
    const exportFileDefaultName = `zavlahovy-system-${new Date().toISOString().slice(0,10)}.json`;
    
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
    
    showNotification('Nastavenia exportované', 'success');
}

function importSettings(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const settings = JSON.parse(e.target.result);
            showConfirm('Naozaj chcete importovať tieto nastavenia?', function() {
                $.ajax({
                    url: '/api/settings/import',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify(settings),
                    success: function() {
                        showNotification('Nastavenia importované', 'success');
                        loadSettings();
                    },
                    error: function() {
                        showNotification('Chyba pri importe', 'error');
                    }
                });
            });
        } catch (e) {
            showNotification('Neplatný súbor', 'error');
        }
    };
    reader.readAsText(file);
    
    // Vyčistiť input
    $('#import-file').val('');
}

function resetToDefaults() {
    showConfirm('Obnoviť predvolené nastavenia? Táto akcia sa nedá vrátiť!', function() {
        showLoader();
        
        $.ajax({
            url: '/api/settings/reset',
            method: 'POST',
            success: function() {
                hideLoader();
                showNotification('Predvolené nastavenia obnovené', 'success');
                loadSettings();
            },
            error: function() {
                hideLoader();
                showNotification('Chyba pri obnovení nastavení', 'error');
                loadDefaultSettings(); // Pre vývoj
            }
        });
    }, true);
}

function restartApp() {
    showNotification('Reštartujem aplikáciu...', 'info');
    setTimeout(() => {
        window.location.reload();
    }, 2000);
}

function shutdownPi() {
    showNotification('Vypínam Raspberry Pi...', 'warning');
    $.ajax({
            url: '/api/system/shutdown',
            method: 'POST',
            success: function() {
                // Žiadna odpoveď – systém sa vypína
            },
            error: function() {
                showNotification('Chyba pri vypínaní', 'error');
            }
    });
    setTimeout(() => {
        showNotification('Systém vypnutý', 'success');
    }, 5000);
}

function rebootPi() {
    showNotification('Reštartujem Raspberry Pi...', 'warning');
    $.ajax({
            url: '/api/system/reboot',
            method: 'POST',
            success: function() {
                // Žiadna odpoveď – systém sa reštartuje
            },
            error: function() {
                showNotification('Chyba pri reštarte', 'error');
            }
    });
    
    setTimeout(() => {
        showNotification('Systém sa reštartuje', 'success');
    }, 5000);
}

function updateDateTime() {
    const now = new Date();
    const datetime = now.toLocaleDateString('sk-SK') + ' ' + 
                    now.toLocaleTimeString('sk-SK', {hour: '2-digit', minute: '2-digit', second: '2-digit'});
    $('#current-datetime').text(datetime);
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
    const notification = $('#notification');
    notification.text(message)
        .removeClass('success error warning info')
        .addClass(type)
        .fadeIn();
    
    setTimeout(() => {
        notification.fadeOut();
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

// Načítanie stavu auto‑startu z API
function loadAutoStartStatus() {
    $.ajax({
        url: '/api/system/autostart-status',
        method: 'GET',
        dataType: 'json',
        success: function(data) {
            const select = $('#auto-start');
            if (data.enabled) {
                select.val('yes');
                $('#auto-start-status').html('<span class="status-ok">✅ Auto‑start zapnutý</span>');
            } else {
                select.val('no');
                $('#auto-start-status').html('<span class="status-error">❌ Auto‑start vypnutý</span>');
            }
        },
        error: function() {
            $('#auto-start-status').html('<span class="status-error">❌ Nepodarilo sa načítať stav auto‑startu</span>');
        }
    });
}

// Uloženie nastavenia auto‑startu pri zmene selectu
function saveAutoStartSetting(value) {
    const enable = (value === 'yes');
    showConfirm(`Nastaviť automatické spúšťanie systému pri štarte na ${enable ? 'ZAPNUTÉ' : 'VYPNUTÉ'}?`, function() {
        $.ajax({
            url: '/api/system/autostart',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ enable: enable }),
            success: function(response) {
                showNotification(`Auto‑start ${response.enabled ? 'zapnutý' : 'vypnutý'}`, 'success');
                loadAutoStartStatus(); // obnoví zobrazenie
            },
            error: function(xhr) {
                let msg = 'Chyba pri zmene auto‑startu';
                try {
                    const resp = JSON.parse(xhr.responseText);
                    if (resp.error) msg = resp.error;
                } catch(e) {}
                showNotification(msg, 'error');
                loadAutoStartStatus(); // vráti pôvodný stav
            }
        });
    }, false);
}


