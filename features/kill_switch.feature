Feature: Prevent excess bandwidth usage in case of a bug
    In order to prevent exceeding my bandwidth cap
    As the client of a lame ISP
    I should be able to prevent bugs from causing excessive bandwidth usage

    Scenario: A backup triggers the kill switch
        Given the value of bw_err in section test_host_2 is 10
        When I invoke backup with the arguments "-vv"
        Then the program should exit 1

    Scenario: Manual override
        Given the value of bw_err in section test_host_2 is 10
        When I invoke backup without parameters
        And I invoke backup with the arguments "test_host_2 --force"
        Then the program should exit 0
