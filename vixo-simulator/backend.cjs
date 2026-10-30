"use strict";
// LOCAL QA backend only. No network calls to VIXO, no real account grants.
const http=require("node:http"),fs=require("node:fs"),path=require("node:path");
const output=path.join(__dirname,"output","ledger.json");
const state={wallets:{},launches:[]};
function save(){fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(state,null,2));}
const server=http.createServer(async(req,res)=>{
  const done=(status,data)=>{res.writeHead(status,{"Content-Type":"application/json"});res.end(JSON.stringify(data));};
  try {
    if(req.url==="/health")return done(200,{healthy:true,test:true});
    const parts=[];for await(const chunk of req)parts.push(chunk);
    const body=parts.length?JSON.parse(Buffer.concat(parts).toString()):{};
    if(req.url==="/login"&&req.method==="POST"){
      if(!["qa-one","qa-two"].includes(body.userId))return done(403,{error:"QA accounts only"});
      return done(200,{userId:body.userId,token:"qa:"+body.userId});
    }
    const auth=(req.headers.authorization||"").replace(/^Bearer qa:/,"");
    if(!["qa-one","qa-two"].includes(auth))return done(401,{error:"QA token required"});
    if(req.url==="/session"&&req.method==="POST"){
      if(!/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i.test(body.launchId||""))
        return done(400,{error:"invalid UUID"});
      if(!state.launches.some(x=>x.uid===auth&&x.id===body.launchId))
        state.launches.push({uid:auth,id:body.launchId});
      save();return done(200,{id:body.launchId,registered:true});
    }
    if(req.url==="/grant"&&req.method==="POST"){
      state.wallets[auth]=9999;save();return done(200,{credits:9999});
    }
    if(req.url==="/spend"&&req.method==="POST"){
      if(body.amount!==100)return done(400,{error:"Only 100-credit QA spend"});
      if((state.wallets[auth]||0)<100)return done(409,{error:"insufficient"});
      state.wallets[auth]-=100;save();return done(200,{credits:state.wallets[auth]});
    }
    if((req.url==="/api/rest/user/points/info" || req.url==="/balance")&&req.method==="GET")return done(200,{credits:state.wallets[auth]||0});
    done(404,{error:"Not found"});
  }catch(e){done(500,{error:String(e)});}
});
server.listen(18777,"127.0.0.1",()=>console.log("QA credit test API on localhost:18777"));
