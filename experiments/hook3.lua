-- AddHook called from inside RunThread.
-- Result: string label 0 events, numeric label 1 event. The string label stays as the probe.
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
return 'hook installed inside a thread'
