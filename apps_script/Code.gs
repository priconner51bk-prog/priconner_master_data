/** Google Sheets -> GitHub JSON synchronizer. Set GITHUB_REPO, GITHUB_TOKEN in Script Properties. */
function syncMasterDataToGitHub() {
  var props = PropertiesService.getScriptProperties(), repo = props.getProperty('GITHUB_REPO'), token = props.getProperty('GITHUB_TOKEN');
  if (!repo || !token) throw new Error('GITHUB_REPO and GITHUB_TOKEN are required Script Properties');
  var book = SpreadsheetApp.getActiveSpreadsheet();
  var characters = readRows_(book, 'characters'), bosses = readRows_(book, 'clan_battle_bosses');
  validate_(characters, 'characters'); validate_(bosses, 'clan_battle_bosses');
  characters = addDynamicAliases_(characters); bosses = addDynamicAliases_(bosses);
  var metadata = readMetadata_(book), payload = {schema_version: metadata.schema_version || '1', source: metadata.source || 'google-sheets', source_commit: metadata.source_commit || 'sheet-managed', generated_at: new Date().toISOString(), characters: characters, clan_battle_bosses: bosses, alias_collisions: detectAliasCollisions_(characters, bosses)};
  var path = props.getProperty('GITHUB_PATH') || 'dist/master_data.json', current = github_(repo, path, token, 'GET', null);
  var request = {message: 'chore: sync master data from Google Sheets', content: Utilities.base64Encode(JSON.stringify(payload, null, 2) + '\n')};
  if (current && current.sha) request.sha = current.sha;
  github_(repo, path, token, 'PUT', request);
  return {path: path, characters: characters.length, clan_battle_bosses: bosses.length};
}

// Pull generated master data from GitHub and restore missing rows in Sheets.
// Requires the same GITHUB_REPO, GITHUB_TOKEN, and optional GITHUB_PATH properties.
function syncMasterDataFromGitHub() {
  var props = PropertiesService.getScriptProperties(), repo = props.getProperty('GITHUB_REPO'), token = props.getProperty('GITHUB_TOKEN');
  if (!repo || !token) throw new Error('GITHUB_REPO and GITHUB_TOKEN are required Script Properties');
  var path = props.getProperty('GITHUB_PATH') || 'dist/master_data.json';
  var current = github_(repo, path, token, 'GET', null);
  if (!current || !current.content) throw new Error('GitHub file was not found: ' + path);
  var json = Utilities.newBlob(Utilities.base64Decode(String(current.content).replace(/\n/g, ''))).getDataAsString('UTF-8');
  var payload = JSON.parse(json);
  applyGeneratedMasterData(payload);
  return {path: path, characters: (payload.characters || []).length, clan_battle_bosses: (payload.clan_battle_bosses || []).length};
}

// Run once manually to keep the spreadsheet synchronized with GitHub hourly.
function installMasterDataTrigger() {
  ScriptApp.getProjectTriggers().forEach(function(t) {
    if (t.getHandlerFunction() === 'syncMasterDataFromGitHub') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('syncMasterDataFromGitHub').timeBased().everyHours(1).create();
}

// Recovery/update helper: copy sheets are read-only sources; only the name column is written.
function updateNamesFromCopies() {
  var book = SpreadsheetApp.getActiveSpreadsheet();
  updateNameColumn_(book, 'characters', 'characters のコピー');
  updateNameColumn_(book, 'clan_battle_bosses', 'clan_battle_bosses のコピー');
}

function updateNameColumn_(book, targetName, sourceName) {
  var target = book.getSheetByName(targetName), source = book.getSheetByName(sourceName);
  if (!target || !source) throw new Error('missing sheet: ' + targetName + ' or ' + sourceName);
  var tv = target.getDataRange().getValues(), sv = source.getDataRange().getValues();
  var th = headerMap_(tv[0]), sh = headerMap_(sv[0]);
  if (th.id === undefined || th.name === undefined || sh.id === undefined || sh.name === undefined) {
    throw new Error('id/name headers are required: ' + targetName);
  }
  var names = {};
  sv.slice(1).forEach(function(r) { if (r[sh.id] !== '') names[String(r[sh.id])] = String(r[sh.name] || ''); });
  var out = tv.slice(1).map(function(r) {
    return [names[String(r[th.id])] === undefined ? r[th.name] : names[String(r[th.id])]];
  });
  // Only this one-column range is written; all other columns remain untouched.
  if (out.length) target.getRange(2, th.name + 1, out.length, 1).setValues(out);
  if (th.aliases !== undefined) {
    var aliases = tv.slice(1).map(function(r, i) {
      var raw = r[th.aliases], current = raw === '' ? [] : JSON.parse(String(raw));
      if (!Array.isArray(current)) throw new Error('aliases must be an array: ' + targetName);
      if (current.length === 0) {
        var base = String(out[i][0] || '').replace(/[（(].*[）)]\s*$/, '').trim() || String(out[i][0] || '').trim();
        if (base && base !== String(out[i][0] || '').trim()) current = [base];
      }
      return [JSON.stringify(current)];
    });
    if (aliases.length) target.getRange(2, th.aliases + 1, aliases.length, 1).setValues(aliases);
  }
  return {target: targetName, updated: out.length};
}

// Apply generated upstream results to both sheets without replacing existing rows.
function applyGeneratedMasterData(payload) {
  var book = SpreadsheetApp.getActiveSpreadsheet();
  upsertTable_(book.getSheetByName('characters'), payload.characters || []);
  upsertTable_(book.getSheetByName('clan_battle_bosses'), payload.clan_battle_bosses || []);
}

function upsertTable_(sheet, incoming) {
  if (!sheet) throw new Error('missing target sheet');
  var values = sheet.getDataRange().getValues(), headers = headerMap_(values[0]);
  if (headers.id === undefined || headers.name === undefined) throw new Error('id/name headers are required');
  var rows = values.slice(1), positions = {};
  rows.forEach(function(r, i) { if (r[headers.id] !== '') positions[String(r[headers.id])] = i; });
  incoming.forEach(function(item) {
    var key = String(item.id), index = positions[key];
    if (index !== undefined) {
      rows[index][headers.name] = String(item.name || '');
      if (headers.name_en !== undefined && item.name_en !== undefined) rows[index][headers.name_en] = String(item.name_en || '');
      if (headers.release !== undefined && item.release !== undefined) rows[index][headers.release] = String(item.release || '');
      return;
    }
    var row = new Array(values[0].length).fill('');
    row[headers.id] = Number(item.id); row[headers.name] = String(item.name || '');
    if (headers.name_en !== undefined) row[headers.name_en] = String(item.name_en || '');
    if (headers.release !== undefined) row[headers.release] = String(item.release || '');
    if (headers.aliases !== undefined) row[headers.aliases] = JSON.stringify(item.aliases || []);
    rows.push(row); positions[key] = rows.length - 1;
  });
  // Keep restored and updated rows in deterministic ID order.
  rows.sort(function(a, b) {
    return Number(a[headers.id]) - Number(b[headers.id]);
  });
  if (rows.length) sheet.getRange(2, 1, rows.length, values[0].length).setValues(rows);
}

function headerMap_(headers) {
  var out = {};
  headers.forEach(function(h, i) { if (h !== '') out[String(h)] = i; });
  return out;
}
function readRows_(book, name) {
  var sheet = book.getSheetByName(name); if (!sheet) throw new Error('missing sheet: ' + name);
  var values = sheet.getDataRange().getValues(), h = headerMap_(values[0]);
  if (values.length < 1 || h.id === undefined || h.name === undefined || h.name_en === undefined || h.aliases === undefined) throw new Error('invalid headers: ' + name);
  return values.slice(1).filter(function(r) { return r[h.id] !== ''; }).map(function(r) {
    var raw = r[h.aliases], a = raw === '' ? [] : JSON.parse(String(raw));
    if (!Array.isArray(a)) throw new Error('aliases must be an array: ' + name);
    return {id: Number(r[h.id]), name: String(r[h.name]), name_en: String(r[h.name_en] || ''), aliases: a.map(String)};
  }).sort(function(a,b) { return a.id-b.id; });
}
function readMetadata_(book) { var s=book.getSheetByName('metadata'); if (!s) return {}; var v=s.getDataRange().getValues(), out={}; if (v.length<2) return out; v[0].forEach(function(k,i) { if(k) out[String(k)]=String(v[1][i]||''); }); return out; }
function validate_(rows, name) { var ids={}; rows.forEach(function(r) { if(!Number.isInteger(r.id)||r.id<=0||ids[r.id]) throw new Error('invalid/duplicate ID in '+name); if(!r.name.trim()) throw new Error('missing name in '+name); ids[r.id]=true; r.aliases.forEach(function(a) { if(!String(a).trim()) throw new Error('empty alias in '+name); }); }); }
function detectAliasCollisions_(characters, bosses) { var seen={}, out=[]; characters.concat(bosses).forEach(function(r) { r.aliases.forEach(function(a) { seen[a]=seen[a]||[]; if(seen[a].indexOf(r.id)<0)seen[a].push(r.id); }); }); Object.keys(seen).forEach(function(a) { if(seen[a].length>1)out.push({alias:a,ids:seen[a]}); }); return out.sort(function(a,b){return a.alias.localeCompare(b.alias);}); }
function addDynamicAliases_(rows) { return rows.map(function(r) { var m=r.name.match(/^(.*?)[（(].*[）)]\s*$/), alias=(m && m[1].trim()) || r.name.trim(); if(r.aliases.length===0 && alias) r.aliases.push(alias); return r; }); }
function github_(repo,path,token,method,body) { var o={method:method,muteHttpExceptions:true,headers:{Authorization:'Bearer '+token,Accept:'application/vnd.github+json'}}; if(body){o.contentType='application/json';o.payload=JSON.stringify(body);} var r=UrlFetchApp.fetch('https://api.github.com/repos/'+repo+'/contents/'+path,o), c=r.getResponseCode(); if(method==='GET'&&c===404)return null; if(c<200||c>=300)throw new Error('GitHub API '+c+': '+r.getContentText()); return JSON.parse(r.getContentText()); }
