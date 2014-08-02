Feature: Provide a logging system
    In order to understand and correct problems
    As a system administrator
    I should have access to a flexible and detailed logging facility

    Scenario: A backup from the command line
        When I invoke backup with the arguments "-v"
        Then the program should exit 0
        And I should see "Processing"
        And test_host's 1st hourly snapshot should contain "backup.log"

    Scenario: Print the output of rsync also
        When I invoke backup with the arguments "-v -p"
        Then the program should exit 0
        And I should see "sending incremental"
        And I should see "total size is"
