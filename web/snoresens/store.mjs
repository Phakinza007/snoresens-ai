const NAME='snoresens-local',TABLE='recordings';
let connection;
function open() {
  if(!connection)connection=new Promise((resolve,reject)=>{
    const request=indexedDB.open(NAME,1);
    request.onupgradeneeded=()=>request.result.createObjectStore(TABLE,{keyPath:'id'});
    request.onsuccess=()=>resolve(request.result);
    request.onerror=()=>{connection=null;reject(request.error);};
    request.onblocked=()=>{connection=null;reject(new Error('ปิดแท็บ Snoresens อื่นแล้วลองอีกครั้ง'));};
  });
  return connection;
}
async function transaction(mode,operation) {
  const db=await open();
  return new Promise((resolve,reject)=>{
    const tx=db.transaction(TABLE,mode);const req=operation(tx.objectStore(TABLE));
    tx.oncomplete=()=>resolve(req.result);
    tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error||new Error('บันทึกข้อมูลไม่สำเร็จ'));
  });
}
export const listRecords=async()=>(await transaction('readonly',s=>s.getAll())).sort((a,b)=>b.createdAt.localeCompare(a.createdAt));
export const saveRecord=record=>transaction('readwrite',s=>s.put(record));
export const deleteRecord=id=>transaction('readwrite',s=>s.delete(id));
export const clearRecords=()=>transaction('readwrite',s=>s.clear());
