from hwtest.plugin import Plugin


class ReportPrompt(Plugin):

    def register(self, manager):
        super(ReportPrompt, self).register(manager)
        self._manager.reactor.call_on(("interface", "show-report"),
            self.show_report)
 
    def show_report(self, interface):
        # This could show a progress bar but it's very fast since most
        # information is available from the gather event type.
        self._manager.reactor.fire("report")


factory = ReportPrompt
