class IssueDetector:
    def detect(self, code):
        issues = []

        lines = code.split("\n")
        if len(lines) > 80:
            issues.append({
                "type": "LongFile",
                "description": f"File is {len(lines)} lines long."
            })

        return issues