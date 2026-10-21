-- Quick Start: hook dialog dan tampilkan teks sederhana

AddHook('OnVariant', 'block_dialog', function(var)
  if var[0] == 'OnDialogRequest' then
    LogToConsole('Dialog diblokir oleh script')
    return true
  end
end)

AddHook('OnSendPacket', 101, function(type, text)
  if text:find('/hi') then
    LogToConsole('Halo dari Bothax Lua!')
    return true
  end
end)

