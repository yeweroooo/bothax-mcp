-- Uji AddHook dari dalam RunThread.
-- Hasil: label string tetap 0 event, label angka 1 event.
_PKT3 = {}
RunThread(function()
  AddHook('OnSendPacketRaw', 'rec3', function(p)
    if type(_PKT3) ~= 'table' or #_PKT3 >= 300 then return end
    _PKT3[#_PKT3 + 1] = string.format(
      'type=%s state=%s value=%s netid=%s x=%s y=%s px=%s py=%s',
      tostring(p.type), tostring(p.state), tostring(p.value or p.int_data),
      tostring(p.netid), tostring(p.x), tostring(p.y), tostring(p.px), tostring(p.py))
  end)
  Sleep(8000)
  RemoveHook('rec3')
end)
return 'hook dipasang di thread'
