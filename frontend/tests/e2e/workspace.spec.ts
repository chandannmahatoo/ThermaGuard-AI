import {test,expect,type Page} from '@playwright/test';
const runtimeErrors=new WeakMap<Page,string[]>();
test.beforeEach(({page})=>{const errors:string[]=[];runtimeErrors.set(page,errors);page.on('pageerror',e=>errors.push(e.message))});
test.afterEach(({page})=>{expect(runtimeErrors.get(page)).toEqual([])});
const event={id:'E2E-thermal-001',latitude:22.5,longitude:79.5,is_demo:true,start_time:'2026-09-13T00:00:00Z',last_seen_time:'2026-09-13T01:00:00Z',duration_hours:1,detection_count:3,mean_frp:12,max_frp:20,mean_brightness:320,persistence_days:1,classification:{predicted_class:'industrial_fire',classification_confidence:.7,model_version:'test-only'},context:{},risk:{risk_score:85,risk_level:'Critical',risk_factors:{thermal:20},missing_context:['weather'],abnormality:{baseline_available:false,abnormality_score:null,abnormality_status:'unavailable'}}};
async function setup(page:Page){
 // Fixtures exist only in tests. No backend state or real tokens are used.
 await page.addInitScript(()=>sessionStorage.setItem('thermaguard.token','e2e-fixture-not-a-real-token'));
 await page.route('**/health',r=>r.fulfill({json:{status:'ok',demo_mode:true}}));
 await page.route('**/api/v1/**',async route=>{
  const path=new URL(route.request().url()).pathname.replace('/api/v1','');
  if(route.request().method()!=='GET')return route.fulfill({status:405,json:{detail:'Unexpected test mutation'}});
  const responses:Record<string,unknown>={
   '/auth/me':{id:1,email:'evaluator@example.test',role:'admin',organization_id:null},'/events':[event,{...event,id:'E2E-thermal-002',persistence_days:3,classification:{...event.classification,classification_confidence:.5}}],'/alerts':[],
   '/model/status':{model_available:false,training_ready:false,eligible_labeled_rows:0,feature_version:'test-only',model_version:null,reason:'No evaluated model'},
   '/model/metrics':{available:false,reason:'No evaluated model'},'/model/review-candidates':{candidates:[]},'/model/review-readiness':{reviewed_rows:0,eligible_rows:0,classes_present:0,classes_total:5,split_groups:0,training_ready:false,missing:[],problems:[]},
   '/providers/status':{providers:{firms:{status:'configured'}}},'/firms/status':{available:false,configured:false,mode:'DEMO',reason:'Test fixture',last_success:null},'/eonet/events':{available:false,reason:'Test fixture',events:[]},
   '/auth/notifications':{notifications_enabled:false,latitude:null,longitude:null,alert_radius_km:10},'/analytics/trends':[], '/admin/organizations':[], '/admin/assignments':[],
   [`/events/${event.id}/evidence`]:{event,detected_facts:[],model_interpretation:event.classification,risk_assessment:event.risk},[`/events/${event.id}/history`]:[],
  };
  return route.fulfill(path in responses?{json:responses[path]}:{status:404,json:{detail:'No test fixture for endpoint'}});
 });
 await page.goto('/');await expect(page.locator('#workspace-content')).toBeVisible();
}
async function navigate(page:Page,name:string){
 const toggle=page.getByRole('button',{name:'Toggle navigation sidebar'});
 if(await toggle.isVisible())await toggle.click();
 await page.getByRole('navigation',{name:'Workspace views'}).getByRole('button',{name,exact:true}).click();
}
for(const width of [320,375,768,1024,1440])test(`workspace responsive at ${width}px`,async({page})=>{
 await page.setViewportSize({width,height:900});await setup(page);
 for(const view of ['Overview','Live Map','Events','Alerts','Analytics','AI Copilot','Providers','Model','Review & Labels','Intelligence Lab','System status','Settings']){
  if(view!=='Overview')await navigate(page,view);
  await expect(page.locator('#workspace-content')).toBeVisible();
  await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),{message:`${view} has viewport overflow at ${width}px`}).toBe(true);
  if(view==='Overview'||view==='Providers')await page.screenshot({path:`test-results/layout-${width}-${view}.png`,fullPage:false});
 }
 await expect(page.getByRole('button',{name:'Enable Browser Push'})).toBeDisabled();
});
test('event selection opens evidence and Escape closes the drawer',async({page})=>{
 await setup(page);await navigate(page,'Events');await page.getByRole('button',{name:/E2E-thermal-001/}).click();await expect(page.getByRole('dialog')).toBeVisible();await page.keyboard.press('Escape');await expect(page.getByRole('dialog')).toHaveCount(0);
});
test('mobile navigation traps focus, closes on Escape, restores toggle',async({page})=>{
 await page.setViewportSize({width:375,height:800});await setup(page);const toggle=page.getByRole('button',{name:'Toggle navigation sidebar'});await toggle.click();const drawer=page.getByRole('dialog',{name:'Workspace navigation'});await expect(drawer).toBeVisible();await page.keyboard.press('Shift+Tab');await expect.poll(()=>drawer.evaluate(el=>el.contains(document.activeElement))).toBe(true);await page.keyboard.press('Escape');await expect(drawer).toHaveCount(0);await expect(toggle).toBeFocused();
});
test('model failure has retry and does not blank the workspace',async({page})=>{
 await setup(page);await page.route('**/api/v1/model/metrics',r=>r.fulfill({status:503,json:{detail:'Evaluation temporarily unavailable'}}));await navigate(page,'Model');await expect(page.locator('#workspace-content').getByRole('alert')).toContainText('Evaluation temporarily unavailable');await expect(page.getByRole('button',{name:'Try again'})).toBeVisible();
});
test('risk filter persists on reload',async({page})=>{
 await setup(page);await page.locator('.map-section-controls').getByRole('combobox',{name:'Risk filter',exact:true}).selectOption('High');await expect(page).toHaveURL(/risk=High/);await page.reload();await expect(page.locator('.map-section-controls').getByRole('combobox',{name:'Risk filter',exact:true})).toHaveValue('High');
});
test('evaluated model renders actual held-out metrics and confusion counts',async({page})=>{
 await setup(page);await page.route('**/api/v1/model/metrics',r=>r.fulfill({json:{algorithm:'RandomForestClassifier',training_rows:30,classes:['industrial_fire'],features:['mean_frp'],validation:{rows:5,accuracy:.8,per_class:{industrial_fire:{precision:.8,recall:1,'f1-score':.89,support:5}},confusion_matrix:[[4]]},test:{rows:5,accuracy:.6,confusion_matrix:[[3]]},split_counts:{train:20,validation:5,test:5},split_groups:{train:['a'],validation:['b'],test:['c']}}}));await navigate(page,'Model');await expect(page.getByText('80.0%',{exact:true})).toHaveCount(2);await expect(page.getByRole('region',{name:'test confusion matrix',exact:true})).toContainText('3');await expect(page.getByText(/Small or unreported sample size/)).toBeVisible();
});
test('expired authentication returns to login without exposing workspace',async({page})=>{
 await setup(page);await page.route('**/api/v1/auth/me',r=>r.fulfill({status:401,json:{detail:'Session expired'}}));await page.reload();await expect(page.getByRole('button',{name:'Sign in to Workspace'})).toBeVisible();await expect(page.locator('#workspace-content')).toHaveCount(0);
});
test('public login validation and small-screen layout',async({page})=>{
 await page.setViewportSize({width:320,height:800});await page.route('**/health',r=>r.fulfill({json:{status:'ok',demo_mode:true}}));await page.goto('/');await page.getByRole('banner').getByRole('button',{name:'Sign In',exact:true}).click();await expect(page.getByRole('button',{name:'Sign in to Workspace'})).toBeVisible();await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
});
test('notification load failures show retry instead of endless loading',async({page})=>{
 await setup(page);await page.route('**/api/v1/auth/notifications',r=>r.fulfill({status:503,json:{detail:'Unavailable'}}));await page.reload();await expect(page.locator('#workspace-content')).toBeVisible();await navigate(page,'Settings');await expect(page.locator('#workspace-content').getByRole('alert')).toContainText('Notification preferences could not be loaded');await expect(page.getByRole('button',{name:'Try again'})).toBeVisible();
});
test('provider refresh failure keeps previous telemetry with a stale notice',async({page})=>{
 await setup(page);await navigate(page,'Providers');await expect(page.getByText('Configured',{exact:true})).toHaveCount(2);await navigate(page,'Events');await page.route('**/api/v1/providers/status',r=>r.fulfill({status:503,json:{detail:'Unavailable'}}));await navigate(page,'Providers');await expect(page.getByText('Previously recorded telemetry shown; refresh failed.')).toBeVisible();await expect(page.getByText('Configured',{exact:true})).toHaveCount(2);
});
for(const width of [320,375,768,1024,1440])test(`intelligence tools fit ${width}px`,async({page})=>{
 await page.setViewportSize({width,height:900});await setup(page);await navigate(page,'Intelligence Lab');
 for(const name of ['Event intelligence','Review intelligence','Compare & watch','History & trends','Operations','Reports & judge mode','Future workflows']){
  await page.getByRole('navigation',{name:'Intelligence tools'}).getByRole('button',{name,exact:true}).click();
  await expect.poll(()=>page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),{message:`${name} overflow at ${width}px`}).toBe(true);
 }
 await expect(page.getByRole('button',{name:'Rollback model',exact:true})).toBeDisabled();
});
test('local comparison and watchlist use existing events and survive reload',async({page})=>{
 await setup(page);await navigate(page,'Intelligence Lab');await page.getByRole('button',{name:'Compare & watch',exact:true}).click();await page.getByLabel('E2E-thermal-001',{exact:true}).check();await page.getByLabel('E2E-thermal-002',{exact:true}).check();await expect(page.getByRole('region',{name:'Event comparison'})).toContainText('Completeness');await page.locator('.comparison-picker>div').filter({hasText:'E2E-thermal-001'}).getByRole('button',{name:'Watch',exact:true}).click();await page.reload();await expect(page.locator('#workspace-content')).toBeVisible();await navigate(page,'Intelligence Lab');await page.getByRole('button',{name:'Compare & watch',exact:true}).click();await expect(page.locator('.comparison-picker>div').filter({hasText:'E2E-thermal-001'}).getByRole('button',{name:'Unwatch',exact:true})).toBeVisible();
});
test('unsupported natural search explains limitations without a search API',async({page})=>{
 await setup(page);await navigate(page,'Intelligence Lab');await page.getByRole('button',{name:'Compare & watch',exact:true}).click();await page.getByLabel('Query',{exact:true}).fill('Predict next month fires');await expect(page.getByText(/Pattern unsupported/)).toBeVisible();await expect(page.locator('.comparison-picker input')).toHaveCount(0);
});
test('event intelligence labels derived quality separately and prints real-mode labels',async({page})=>{
 await setup(page);await navigate(page,'Intelligence Lab');await expect(page.getByText('UI evidence completeness',{exact:true})).toBeVisible();await expect(page.getByText('Model confidence',{exact:true})).toBeVisible();await page.getByRole('button',{name:'Reports & judge mode',exact:true}).click();await expect(page.locator('.report-document')).toContainText('DEMO');await page.emulateMedia({media:'print'});await expect(page.locator('.sidebar')).not.toBeVisible();await expect(page.locator('.report-document')).toBeVisible();
});
