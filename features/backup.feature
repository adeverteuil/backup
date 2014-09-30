Feature: Backup a directory to another directory
    In order to maintain best practices in system administration
    As a system administrator
    I should be able to do regular backups

    Scenario: Do the first backup.
        Given the test_host directory is empty
        When I invoke backup without parameters
        Then the program should exit 0
        And the test_host directory should contain 1 hourly snapshots
        And the test_host directory should contain 0 daily snapshots
        And the test_host directory should contain no hidden files

    Scenario: The second hourly backup.
        When I invoke backup without parameters
        And the snapshots in test_host age 1 hours
        And the snapshots in test_host_2 age 1 hours
        And I invoke backup without parameters
        Then the program should exit 0
        And the test_host directory should contain 2 hourly snapshots
        And the test_host directory should contain 0 daily snapshots

    Scenario: Multiple hosts to back up.
        When I invoke backup with the arguments "test_host test_host_2"
        Then the program should exit 0
        And the test_host directory should contain 1 hourly snapshots
        And the test_host_2 directory should contain 1 hourly snapshots
