Feature: Provide a logging system
    In order to understand and correct problems
    As a system administrator
    I should have access to a flexible and detailed logging facility

    @wip
    Scenario: A backup from the command line
        When I invoke backup with the arguments "-v"
        Then the program should exit 0
        And I should see "sending incremental"
        And I should see "total size is"
        And test_host's 1st hourly snapshot should contain "backup.log"
