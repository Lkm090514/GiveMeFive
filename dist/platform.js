// Non-secure preview origins lack CacheStorage/randomUUID. Production HTTPS uses native APIs.
(function(root){
 if(!crypto.randomUUID)crypto.randomUUID=()=>{const b=crypto.getRandomValues(new Uint8Array(16));b[6]=(b[6]&15)|64;b[8]=(b[8]&63)|128;const h=[...b].map(n=>n.toString(16).padStart(2,'0')).join('');return `${h.slice(0,8)}-${h.slice(8,12)}-${h.slice(12,16)}-${h.slice(16,20)}-${h.slice(20)}`;};
 root.GMFCacheAvailable=typeof caches!=='undefined';
 if(!root.GMFCacheAvailable)root.caches={open:async()=>({match:async()=>undefined,delete:async()=>true,put:async()=>{throw Error('离线下载需要 HTTPS 或 localhost。');}}),keys:async()=>[],delete:async()=>true};
})(window);
