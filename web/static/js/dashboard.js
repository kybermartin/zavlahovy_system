// web/static/js/dashboard.js
// JavaScript pre dashboard - aktualizácia v reálnom čase

$(document).ready(function() {
    // Okamžitá aktualizácia pri načítaní
    updateStatus();
    
    // Pravidelná aktualizácia každé 3 sekundy
    setInterval(updateStatus, 3000);
});

function updateStatus() {
    $.ajax({
        url: '/api/status',
        method: 'GET',
        dataType: 'json',
        success: function(data) {
            updateDateTime(data);
            updatePumps(data);
            updateValves(data);
            updateActivePlan(data);
        },
        error: function(xhr, status, error) {
            console.error('Chyba pri načítaní stavu:', error);
            $('#tlakove-status').text('Chyba pripojenia').addClass('error');
        }
    });
}

function updateDateTime(data) {
    $('#current-datetime').text(data.datum + ' ' + data.cas);
}

function updatePumps(data) {
    // Tlakové čerpadlo
    const t = data.tlakove;
    $('#tlakove-mode').text(t.mode);
    $('#tlakove-state').text(t.state);
    
    const tStatus = $('#tlakove-status');
    tStatus.removeClass('active inactive error');
    
    if (t.state === 'BEZI') {
        tStatus.text('⏵ BEŽÍ').addClass('active');
        $('#tlakove-okruh-container').show();
        $('#tlakove-tlak-container').show();
        $('#tlakove-okruh').text(t.okruh || '-');
        $('#tlakove-tlak').text((t.tlak || '0') + '%');
    } else {
        tStatus.text('⏸ VYPNUTÉ').addClass('inactive');
        $('#tlakove-okruh-container').hide();
        $('#tlakove-tlak-container').hide();
    }
    
    // Nasávacie čerpadlo
    const n = data.nasavacie;
    $('#nasavacie-mode').text(n.mode);
    $('#nasavacie-state').text(n.state);
    
    const nStatus = $('#nasavacie-status');
    nStatus.removeClass('active inactive error');
    
    if (n.state === 'BEZI') {
        nStatus.text('⏵ BEŽÍ').addClass('active');
    } else {
        nStatus.text('⏸ VYPNUTÉ').addClass('inactive');
    }
}

function updateValves(data) {
    const container = $('#valves-container');
    container.empty();
    
    data.ventily.forEach(function(v) {
        const percent = v.pozicia;
        const isOpen = v.otvoreny;
        
        const valveHtml = `
            <div class="valve-item ${isOpen ? 'open' : 'closed'}">
                <div class="valve-header">Okruh ${v.okruh}</div>
                <div class="valve-status">${isOpen ? 'OTVORENÝ' : 'ZATVORENÝ'}</div>
                <div class="valve-pressure">
                    <div class="pressure-bar" style="width: ${percent}%"></div>
                    <span class="pressure-text">${percent}%</span>
                </div>
            </div>
        `;
        container.append(valveHtml);
    });
}

function updateActivePlan(data) {
    const container = $('#active-plan');
    container.empty();
    
    if (data.aktivny_plan) {
        const p = data.aktivny_plan;
        const html = `
            <div class="plan-details">
                <div class="plan-item">
                    <span class="plan-label">Interval:</span>
                    <span class="plan-value">${p.id || 'manuálny'}</span>
                </div>
                <div class="plan-item">
                    <span class="plan-label">Okruh:</span>
                    <span class="plan-value">${p.okruh}</span>
                </div>
                <div class="plan-item">
                    <span class="plan-label">Tlak:</span>
                    <span class="plan-value">${p.tlak}%</span>
                </div>
                <div class="plan-item">
                    <span class="plan-label">Čas:</span>
                    <span class="plan-value">${p.start || '--:--'} - ${p.stop || '--:--'}</span>
                </div>
            </div>
        `;
        container.append(html);
    } else {
        container.append('<p class="no-plan">Žiadny aktívny plán</p>');
    }
}

function emergencyStop() {
    if (confirm('Naozaj chcete núdzovo zastaviť VŠETKY čerpadlá?')) {
        $.ajax({
            url: '/api/control/pump',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({
                pump: 'tlakove',
                action: 'stop'
            }),
            success: function() {
                $.ajax({
                    url: '/api/control/pump',
                    method: 'POST',
                    contentType: 'application/json',
                    data: JSON.stringify({
                        pump: 'nasavacie',
                        action: 'stop'
                    }),
                    success: function() {
                        alert('Všetky čerpadlá zastavené');
                        updateStatus();
                    }
                });
            }
        });
    }
}

function forceScheduleCheck() {
    $.ajax({
        url: '/api/control/pump',
        method: 'POST',
        contentType: 'application/json',
        data: JSON.stringify({
            pump: 'tlakove',
            action: 'check'
        }),
        success: function() {
            alert('Kontrola plánu vynútená');
            updateStatus();
        }
    });
}