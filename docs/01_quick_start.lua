-- Quick start: block a dialog and react to chat input.
-- Labels are numbers on purpose: string labels register no callback.

AddHook('OnVariant', 1, function(var)
  if var[0] == 'OnDialogRequest' then
    LogToConsole('dialog blocked by the script')
    return true -- returning true swallows the event
  end
end)

AddHook('OnSendPacket', 101, function(typ, text)
  if text:find('/hi') then
    LogToConsole('hello from Bothax Lua!')
    return true
  end
end)
